# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import sys

import docker
import sh
import yaml

from .database import Database
from .executors import LdapExecutor
from .executors import OxauthExecutor
from .executors import OxtrustExecutor
from .executors import HttpdExecutor
from .utils import get_logger
from .utils import decrypt_text
from .utils import expose_cidr

PROVIDER_CONFIG_FILE = "/etc/gluu/provider.yml"
STATE_DISABLED = "DISABLED"
STATE_SUCCESS = "SUCCESS"
RECOVERY_PRIORITY_CHOICES = {
    "ldap": 1,
    "oxauth": 2,
    "httpd": 3,
    "oxtrust": 4,
}


def format_node(data):
    data["recovery_priority"] = RECOVERY_PRIORITY_CHOICES.get(data["type"], 0)
    return data


class RecoveryTask(object):
    def __init__(self, logger=None):
        self.logger = logger or get_logger(
            name=__name__ + "." + self.__class__.__name__
        )

        self.db = Database()

        # as we only need to recover containers locally,
        # we use docker.Client with unix socket connection
        self.docker = docker.Client()

        try:
            with open(PROVIDER_CONFIG_FILE) as fp:
                self.config = yaml.safe_load(fp.read())
        except IOError:
            self.logger.error(
                "unable to read config from {}".format(PROVIDER_CONFIG_FILE)
            )
            sys.exit(1)

    def execute(self):
        provider = self.db.get(self.config["provider_id"], "providers")
        cluster = self.db.get(self.config["cluster_id"], "clusters")

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
            (self.db.where("provider_id") == self.config["provider_id"])
            & (self.db.where("state") == STATE_SUCCESS)
        )

        # attach the recovery priority
        success_nodes = [format_node(node) for node in _nodes]

        # disabled nodes must be recovered so we can enable again when
        # expired license is updated
        _nodes = self.db.search_from_table(
            "nodes",
            (self.db.where("provider_id") == self.config["provider_id"])
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

            self.logger.warn("{} node {} is not running".format(
                node["type"], node["id"]
            ))

            self.logger.info("restarting {} node {}".format(
                node["type"], node["id"]
            ))
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
            executor = exec_cls(node, provider, cluster, self.docker)
            executor.run_entrypoint()
