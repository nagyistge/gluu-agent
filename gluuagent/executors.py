# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import sys
from collections import namedtuple

import etcd
import sh

from .utils import get_logger
from .storages import get_cluster_nodes
from .storages import get_provider_nodes

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
    def __init__(self, node, provider, cluster, docker):
        self.logger = get_logger(name=__name__ + "." + self.__class__.__name__)
        self.node = node
        self.provider = provider
        self.cluster = cluster
        self.docker = docker
        self.kv = etcd.Client()

    def get_node(self, node_id):
        node = {}
        try:
            result = self.kv.read(
                "gluucluster/nodes/{}".format(node_id),
            )
        except etcd.EtcdKeyNotFound:
            self.logger.error(
                "unable to find node with ID {}".format(node_id))
        else:
            node = {
                child.key.split("/")[-1]: child.value
                for child in result.children
            }
        return node


class LdapExecutor(BaseExecutor):
    def run_entrypoint(self):
        cmd = "/opt/opendj/bin/start-ds"
        result = run_docker_exec(self.docker, self.node["id"], cmd)
        if result.exit_code != 0:
            self.logger.error(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )
            self.docker.stop(self.node["id"])


class OxauthExecutor(BaseExecutor):
    def run_entrypoint(self):
        self.add_ldap_hosts()
        self.start_tomcat()

    def start_tomcat(self):
        cmd = "export CATALINA_PID=/opt/tomcat/bin/catalina.pid " \
              " && /opt/tomcat/bin/catalina.sh start"
        result = run_docker_exec(self.docker, self.node["id"], cmd)
        if result.exit_code != 0:
            self.logger.error(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )
            self.docker.stop(self.node["id"])

    def add_ldap_hosts(self):
        try:
            nodes = get_cluster_nodes(self.kv, self.cluster["id"])
        except (etcd.EtcdKeyNotFound, etcd.EtcdConnectionFailed,) as exc:
            self.logger.error(exc)
            sys.exit(1)

        ldap_nodes = [
            self.get_node(node["id"]) for node in nodes
            if node["type"] == "ldap" and node["state"] == "SUCCESS"
        ]

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
        self.start_tomcat()

    def get_httpd_nodes(self):
        try:
            nodes = get_provider_nodes(self.kv, self.provider["id"])
        except (etcd.EtcdKeyNotFound, etcd.EtcdConnectionFailed,) as exc:
            self.logger.error(exc)
            sys.exit(1)

        httpd_nodes = [
            self.get_node(node["id"]) for node in nodes
            if node["type"] == "httpd" and node["state"] == "SUCCESS"
        ]
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
            self.logger.error(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )


class HttpdExecutor(BaseExecutor):
    def run_entrypoint(self):
        cmd = "rm /var/run/apache2/apache2.pid && service apache2 start"
        result = run_docker_exec(self.docker, self.node["id"], cmd)
        if result.exit_code != 0:
            self.logger.error(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )
            self.docker.stop(self.node["id"])

        for port in [80, 443]:
            try:
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
                self.logger.error(exc.stderr.strip())
