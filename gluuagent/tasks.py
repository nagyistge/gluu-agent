# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import abc
import json
import socket
import sys

import docker
import docker.errors
import sh
import yaml

from .constants import STATE_SUCCESS
from .constants import STATE_DISABLED
from .constants import RECOVERY_PRIORITY_CHOICES
from .executors import LdapExecutor
from .executors import OxauthExecutor
from .executors import OxtrustExecutor
from .executors import OxidpExecutor
from .executors import NginxExecutor
from .utils import get_logger
from .utils import decrypt_text
from .utils import get_exposed_cidr
from .utils import get_prometheus_cidr


def format_node(data):
    data["recovery_priority"] = RECOVERY_PRIORITY_CHOICES.get(data["type"], 0)
    # backward-compat for older nodes
    if "domain_name" not in data:
        data["domain_name"] = "{}.{}.gluu.local".format(
            data["id"], data["type"]
        )
    return data


class BaseTask(object):
    @abc.abstractmethod
    def execute(self):
        pass

    def __init__(self, db, logger=None, encrypted=False):
        self.logger = logger or get_logger(
            name=__name__ + "." + self.__class__.__name__
        )
        self.db = db
        self.encrypted = encrypted

        # as we only need to recover containers locally,
        # we use docker.Client with unix socket connection
        self.docker = docker.Client()

    def get_provider(self):
        try:
            # match provider with specific hostname
            #
            # 1. find by FQDN
            # 2. find by hostname of the machine where the Python interpreter
            #    is currently executing
            provider = self.db.search_from_table(
                "providers",
                (self.db.where("hostname") == socket.getfqdn())
                | (self.db.where("hostname") == socket.gethostname()),
            )[0]
            return provider
        except IndexError:
            self.logger.error("provider is not found")
            sys.exit(1)


class RecoveryTask(BaseTask):
    def execute(self):
        try:
            cluster = self.db.all("clusters")[0]
        except IndexError:
            self.logger.error("cluster is not found")
            sys.exit(1)

        provider = self.get_provider()

        self.logger.info("trying to recover {} provider {}".format(
            provider["type"], provider["id"],
        ))

        # recover weave container
        self.recover_weave(provider, cluster)

        # recover all provider's nodes
        self.recover_nodes(provider, cluster)

        # recover prometheus container
        self.recover_prometheus(provider, cluster)

        self.logger.info(
            "recovery process for {} provider {} is finished".format(
                provider["type"], provider["id"])
        )

    def container_stopped(self, container):
        meta = self.docker.inspect_container(container)
        return meta["State"]["Running"] is False

    def recover_prometheus(self, provider, cluster):
        if provider["type"] == "master":
            if not self.container_stopped("prometheus"):
                self.logger.info("prometheus container is already running")
                return

            self.logger.warn("prometheus container is not running")
            self.logger.info("restarting prometheus container")
            self.docker.restart("prometheus")

            addr, prefixlen = get_prometheus_cidr(cluster["weave_ip_network"])
            sh.weave("attach", "{}/{}".format(addr, prefixlen), "prometheus")

    def recover_weave(self, provider, cluster):
        try:
            if not self.container_stopped("weave"):
                self.logger.info("weave container is already running")
                return
        except docker.errors.APIError as exc:
            err_code = exc.response.status_code
            if err_code == 404:
                self.logger.warn(exc)
            else:
                raise

        self.logger.warn("weave container is not running")
        self.logger.info("restarting weave container")

        passwd = ""
        if self.encrypted:
            passwd = decrypt_text(cluster["admin_pw"], cluster["passkey"])

        if provider["type"] == "master":
            sh.weave(
                "launch-router",
                "--password", passwd,
                "--dns-domain", "gluu.local",
                "--ipalloc-range", cluster["weave_ip_network"],
                "--ipalloc-default-subnet", cluster["weave_ip_network"],
            )
        else:
            with open("/etc/salt/minion") as fp:
                config = fp.read()
                opts = yaml.safe_load(config)
                sh.weave(
                    "launch-router",
                    "--password", passwd,
                    "--dns-domain", "gluu.local",
                    "--ipalloc-range", cluster["weave_ip_network"],
                    "--ipalloc-default-subnet", cluster["weave_ip_network"],
                    opts["master"],
                )

        addr, prefixlen = get_exposed_cidr(cluster["weave_ip_network"])
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

                # if weave is relaunched by another tool, DNS entries
                # might not be restored, hence we're readding the entries
                sh.weave("dns-add", node["id"], "-h", node["domain_name"])
                if node["type"] == "ldap":
                    sh.weave("dns-add", node["id"], "-h", "ldap.gluu.local")
                continue

            self.logger.warn("{} node {} is not running; restarting ..".format(
                node["type"], node["id"]
            ))

            self.docker.restart(node["id"])
            if node["state"] == STATE_SUCCESS:
                cidr = "{}/{}".format(node["weave_ip"],
                                      node["weave_prefixlen"])
                self.logger.info("attaching weave IP {}".format(cidr))
                sh.weave("attach", "{}".format(cidr), node["id"])

                self.logger.info("adding {} to local "
                                 "DNS server".format(node["domain_name"]))
                sh.weave("dns-add", node["id"], "-h", node["domain_name"])

                if node["type"] == "ldap":
                    self.logger.info("adding ldap.gluu.local to "
                                     "local DNS server")
                    sh.weave("dns-add", node["id"], "-h", "ldap.gluu.local")
            self.setup_node(node, provider, cluster)

    def setup_node(self, node, provider, cluster):
        executors = {
            "ldap": LdapExecutor,
            "oxauth": OxauthExecutor,
            "oxtrust": OxtrustExecutor,
            "oxidp": OxidpExecutor,
            "nginx": NginxExecutor,
        }

        exec_cls = executors.get(node["type"])
        if exec_cls:
            self.logger.info("running entrypoint for "
                             "{} node {}".format(node["type"], node["id"]))
            executor = exec_cls(node, provider, cluster,
                                self.docker, self.db, self.logger)
            executor.run_entrypoint()


class ImageUpdateTask(BaseTask):
    registry_base_url = "registry.gluu.org:5000"

    images = [
        "gluuopendj",
        "gluuoxauth",
        "gluuoxtrust",
        "gluuoxidp",
        "gluunginx",
    ]

    def execute(self):
        for image in self.images:
            new_image = "{}/{}".format(self.registry_base_url, image)

            # pull the updates from registry
            self.logger.info("pulling {} updates".format(new_image))
            self.pull_image(new_image)

        provider = self.get_provider()
        nodes = self.db.search_from_table(
            "nodes",
            (self.db.where("provider_id") == provider["id"])
            & ((self.db.where("state") == STATE_SUCCESS)
                | (self.db.where("state") == STATE_DISABLED))
        )

        self.logger.info("stopping all nodes for re-provisioning")
        for node in nodes:
            self.docker.stop(node["id"])

        # recover the nodes
        recovery_task = RecoveryTask(self.db, self.logger)
        recovery_task.execute()

    def pull_image(self, image):
        resp = self.docker.pull(repository=image, stream=True)
        output = ""

        while True:
            try:
                output = resp.next()
                self.logger.info(output)
            except StopIteration:
                break

        result = json.loads(output)
        if "errorDetail" in result:
            self.logger.error(result)
            return False
        return True
