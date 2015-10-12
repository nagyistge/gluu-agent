# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import sys

import docker
import etcd
import sh
import yaml

from gluuclusterlib.kv import get_provider
from gluuclusterlib.kv import get_cluster
from gluuclusterlib.kv import get_node
from gluuclusterlib.kv import get_provider_nodes
from gluuclusterlib.crypto import decrypt_text
from gluuclusterlib.network import exposed_weave_ip

from .executors import LdapExecutor
from .executors import OxauthExecutor
from .executors import OxtrustExecutor
from .executors import HttpdExecutor


from .utils import get_logger

PROVIDER_CONFIG_FILE = "/etc/gluu/provider.yml"
STATE_DISABLED = "DISABLED"
STATE_SUCCESS = "SUCCESS"


class RecoveryTask(object):
    def __init__(self):
        self.logger = get_logger(name=__name__ + "." + self.__class__.__name__)

        self.kv = etcd.Client()

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
        try:
            provider = get_provider(self.kv, self.config["provider_id"])
        except (etcd.EtcdKeyNotFound, etcd.EtcdConnectionFailed,) as exc:
            self.logger.error(exc)
            sys.exit(1)

        try:
            cluster = get_cluster(self.kv, self.config["cluster_id"])
        except (etcd.EtcdKeyNotFound, etcd.EtcdConnectionFailed,) as exc:
            self.logger.error(exc)
            sys.exit(1)

        # recover weave container
        self.recover_weave(provider, cluster)

        # recover all provider's nodes
        self.recover_nodes(provider, cluster)

        # recover prometheus container
        self.recover_prometheus(provider)

    def container_stopped(self, container):
        meta = self.docker.inspect_container(container)
        return meta["State"]["Running"] is False

    def recover_prometheus(self, provider):
        if (provider["type"] == "master"
                and self.container_stopped("prometheus")):
            self.logger.warn("prometheus container is not running")
            self.logger.info("restarting prometheus container")
            self.docker.restart("prometheus")

    def recover_weave(self, provider, cluster):
        if self.container_stopped("weave"):
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

            addr, prefixlen = exposed_weave_ip(cluster["weave_ip_network"])
            sh.weave("expose", "{}/{}".format(addr, prefixlen))

    def recover_nodes(self, provider, cluster):
        try:
            nodes = get_provider_nodes(self.kv, provider["id"])
        except (etcd.EtcdKeyNotFound, etcd.EtcdConnectionFailed,) as exc:
            self.logger.error(exc)
            sys.exit(1)

        success_nodes = [
            get_node(self.kv, node["id"]) for node in nodes
            if node["state"] == STATE_SUCCESS
        ]

        # disabled nodes must be recovered so we can enable again when
        # expired license is updated
        disabled_nodes = [
            get_node(self.kv, node["id"]) for node in nodes
            if node["state"] == STATE_DISABLED
        ]

        # sort nodes by its recovery_priority property
        # so we will have a fully recovered nodes
        nodes = sorted(success_nodes + disabled_nodes,
                       key=lambda node: node["recovery_priority"])

        for node in nodes:
            if self.container_stopped(node["id"]):
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
