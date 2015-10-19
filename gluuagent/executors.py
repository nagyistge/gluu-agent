# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

from collections import namedtuple

import sh

from .constants import STATE_SUCCESS
from .utils import get_logger

DockerExecResult = namedtuple("DockerExecResult",
                              ["cmd", "exit_code", "retval"])


def run_docker_exec(client, container, cmd):
    exec_cmd = client.exec_create(
        container,
        cmd='sh -c "{}"'.format(cmd),
    )
    retval = client.exec_start(exec_cmd)
    inspect = client.exec_inspect(exec_cmd)
    result = DockerExecResult(cmd=cmd, exit_code=inspect["ExitCode"],
                              retval=retval.strip())
    return result


class BaseExecutor(object):
    def __init__(self, node, provider, cluster, docker, db, logger=None):
        self.logger = logger or get_logger(
            name=__name__ + "." + self.__class__.__name__
        )
        self.node = node
        self.provider = provider
        self.cluster = cluster
        self.docker = docker
        self.db = db

    def run_entrypoint(self):
        raise NotImplementedError


class LdapExecutor(BaseExecutor):
    def run_entrypoint(self):
        # entrypoint is moved to supervisord
        pass


class OxauthExecutor(BaseExecutor):
    def run_entrypoint(self):
        self.add_ldap_hosts()

    def add_ldap_hosts(self):
        ldap_nodes = self.db.search_from_table(
            "nodes",
            (self.db.where("type") == "ldap")
            & (self.db.where("state") == STATE_SUCCESS)
        )

        for ldap in ldap_nodes:
            # add the entry only if line is not exist in /etc/hosts
            cmd = "grep -q '^{0} {1}$' /etc/hosts " \
                  "|| echo '{0} {1}' >> /etc/hosts" \
                .format(ldap["weave_ip"], ldap["id"])
            result = run_docker_exec(self.docker, self.node["id"], cmd)
            if result.exit_code != 0:
                self.logger.error(
                    "got error with exit code {} while running docker exec; "
                    "reason={}".format(result.exit_code, result.retval)
                )
                self.docker.stop(self.node["id"])


class OxtrustExecutor(OxauthExecutor):
    def run_entrypoint(self):
        self.add_ldap_hosts()

        try:
            # if we already have httpd node in the same provider,
            # add entry to /etc/hosts and import the cert
            httpd = self.get_httpd_nodes()[0]
            self.add_httpd_host(httpd)
            self.import_httpd_cert()
        except IndexError:
            pass

    def get_httpd_nodes(self):
        httpd_nodes = self.db.search_from_table(
            "nodes",
            (self.db.where("type") == "httpd")
            & (self.db.where("state") == "SUCCESS")
        )
        return httpd_nodes

    def add_httpd_host(self, httpd):
        # add the entry only if line is not exist in /etc/hosts
        cmd = "grep -q '^{0} {1}$' /etc/hosts " \
              "|| echo '{0} {1}' >> /etc/hosts" \
            .format(httpd["weave_ip"],
                    self.cluster["ox_cluster_hostname"])
        result = run_docker_exec(self.docker, self.node["id"], cmd)
        if result.exit_code != 0:
            self.logger.error(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )
            self.docker.stop(self.node["id"])

    def import_httpd_cert(self):
        # imports httpd cert into oxtrust cacerts to avoid
        # "peer not authenticated" error
        cmd = "echo -n | openssl s_client -connect {}:443 | " \
              "sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' " \
              "> /tmp/ox.cert".format(self.cluster["ox_cluster_hostname"])
        result = run_docker_exec(self.docker, self.node["id"], cmd)
        if result.exit_code != 0:
            self.logger.error(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )
            self.docker.stop(self.node["id"])

        cmd = " ".join([
            "keytool -importcert -trustcacerts",
            "-alias '{}'".format(self.cluster["ox_cluster_hostname"]),
            "-file /tmp/ox.cert",
            "-keystore {}".format(self.node["truststore_fn"]),
            "-storepass changeit -noprompt",
        ])
        result = run_docker_exec(self.docker, self.node["id"], cmd)
        if result.exit_code != 0:
            # it is safe to have error when importing existing cert
            self.logger.warn(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )


class HttpdExecutor(BaseExecutor):
    def run_entrypoint(self):
        # iptables rules are not persisted, hence we're adding them again
        for port in [80, 443]:
            try:
                self.logger.info("deleting existing iptables rules")
                # delete existing iptables rules (if any) for httpd node
                # to ensure there's always unique rules for the node
                # even when recovery is executed multiple times
                sh.iptables(
                    "-t", "nat",
                    "-D", "PREROUTING",
                    "-p", "tcp",
                    "-i", "eth0",
                    "--dport", port,
                    "-j", "DNAT",
                    "--to-destination", "{}:{}".format(self.node["weave_ip"],
                                                       port),
                )
            except sh.ErrorReturnCode_1 as exc:
                # iptables rules not exist
                self.logger.warn(exc.stderr.strip())

            try:
                self.logger.info("adding new iptables rules")
                sh.iptables(
                    "-t", "nat",
                    "-A", "PREROUTING",
                    "-p", "tcp",
                    "-i", "eth0",
                    "--dport", port,
                    "-j", "DNAT",
                    "--to-destination", "{}:{}".format(self.node["weave_ip"],
                                                       port),
                )
            except sh.ErrorReturnCode_3 as exc:
                self.logger.warn(exc.stderr.strip())
