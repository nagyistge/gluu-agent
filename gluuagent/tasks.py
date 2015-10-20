# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import socket
import sys
import time

import docker
import sh
import yaml

from .constants import STATE_SUCCESS
from .constants import STATE_DISABLED
from .constants import RECOVERY_PRIORITY_CHOICES
from .executors import LdapExecutor
from .executors import OxauthExecutor
from .executors import OxtrustExecutor
from .executors import HttpdExecutor
from .utils import get_logger
from .utils import decrypt_text
from .utils import expose_cidr


def format_node(data):
    data["recovery_priority"] = RECOVERY_PRIORITY_CHOICES.get(data["type"], 0)
    return data


class RecoveryTask(object):
    def __init__(self, db, logger=None):
        self.logger = logger or get_logger(
            name=__name__ + "." + self.__class__.__name__
        )
        self.db = db

        # as we only need to recover containers locally,
        # we use docker.Client with unix socket connection
        self.docker = docker.Client()

    def execute(self):
        try:
            cluster = self.db.all("clusters")[0]
        except IndexError:
            cluster = None

        try:
            provider = self.db.search_from_table(
                "providers",
                self.db.where("hostname") == socket.getfqdn(),
            )[0]
        except IndexError:
            provider = None

        if not any([provider, cluster]):
            self.logger.error("provider or cluster is invalid")
            sys.exit(1)

        self.logger.info("trying to recover {} provider {}".format(
            provider["type"], provider["id"],
        ))

        # recover weave container
        self.recover_weave(provider, cluster)

        # recover all provider's nodes
        self.recover_nodes(provider, cluster)

        # recover prometheus container
        self.recover_prometheus(provider)

        self.logger.info(
            "recovery process for {} provider {} is finished".format(
                provider["type"], provider["id"])
        )

    def container_stopped(self, container):
        meta = self.docker.inspect_container(container)
        return meta["State"]["Running"] is False

    def recover_prometheus(self, provider):
        if provider["type"] == "master":
            if not self.container_stopped("prometheus"):
                self.logger.info("prometheus container is already running")
                return

            self.logger.warn("prometheus container is not running")
            self.logger.info("restarting prometheus container")
            self.docker.restart("prometheus")

    def recover_weave(self, provider, cluster):
        if not self.container_stopped("weave"):
            self.logger.info("weave container is already running")
            return

        self.logger.warn("weave container is not running")
        self.logger.info("restarting weave container")

        passwd = decrypt_text(cluster["admin_pw"], cluster["passkey"])
        if provider["type"] == "master":
            sh.weave("launch", "-password", passwd)
        else:
            with open("/etc/salt/minion") as fp:
                config = fp.read()
                opts = yaml.safe_load(config)
                sh.weave("launch", "-password", passwd, opts["master"])

        addr, prefixlen = expose_cidr(cluster["weave_ip_network"])
        sh.weave("expose", "{}/{}".format(addr, prefixlen))

    def recover_nodes(self, provider, cluster):
        _nodes = self.db.search_from_table(
            "nodes",
            (self.db.where("provider_id") == provider["id"])
            & (self.db.where("state") == STATE_SUCCESS)
        )

        # attach the recovery priority
        success_nodes = [format_node(node) for node in _nodes]

        # disabled nodes must be recovered so we can enable again when
        # expired license is updated
        _nodes = self.db.search_from_table(
            "nodes",
            (self.db.where("provider_id") == provider["id"])
            & (self.db.where("state") == STATE_DISABLED)
        )

        # attach the recovery priority
        disabled_nodes = [format_node(node) for node in _nodes]

        # sort nodes by its recovery_priority property
        # so we will have a fully recovered nodes
        nodes = sorted(success_nodes + disabled_nodes,
                       key=lambda node: node["recovery_priority"])

        for node in nodes:
            if not self.container_stopped(node["id"]):
                self.logger.info("{} node {} is already running".format(
                    node["type"], node["id"]
                ))
                continue

            self.logger.warn("{} node {} is not running; restarting ..".format(
                node["type"], node["id"]
            ))

            # wait for internal routing being ready
            time.sleep(20)

            self.docker.restart(node["id"])
            if node["state"] == STATE_SUCCESS:
                self.logger.info("attaching weave IP")
                sh.weave(
                    "attach",
                    "{}/{}".format(node["weave_ip"],
                                   node["weave_prefixlen"]),
                    node["id"],
                )
            self.setup_node(node, provider, cluster)

    def setup_node(self, node, provider, cluster):
        executors = {
            "ldap": LdapExecutor,
            "oxauth": OxauthExecutor,
            "oxtrust": OxtrustExecutor,
            "httpd": HttpdExecutor,
        }

        exec_cls = executors.get(node["type"])
        if exec_cls:
            self.logger.info("running entrypoint for "
                             "{} node {}".format(node["type"], node["id"]))
            executor = exec_cls(node, provider, cluster,
                                self.docker, self.db, self.logger)
            executor.run_entrypoint()
