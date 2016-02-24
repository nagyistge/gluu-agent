# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import time
from collections import namedtuple

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
        """Entrypoints need to be started/executed after starting container.
        """


class LdapExecutor(BaseExecutor):
    def run_entrypoint(self):
        # nodes like oxauth/oxtrust/saml need ldap to run first;
        # hence we set delay to block other node's executors
        # running simultaneously
        time.sleep(20)


class OxauthExecutor(BaseExecutor):
    def run_entrypoint(self):
        time.sleep(5)
        self.clean_restart_httpd()

    def clean_restart_httpd(self):
        resp = run_docker_exec(self.docker, self.node["id"],
                               "supervisorctl status httpd")
        if "RUNNING" not in resp.retval:
            self.logger.info("httpd process is crashed; restarting ...")
            # httpd refuses to work if previous shutdown was unclean
            # a workaround is to remove ``/var/run/apache2/apache2.pid``
            # before restarting supervisor program
            cmd = "rm /var/run/apache2/apache2.pid " \
                  "&& supervisorctl restart httpd"
            run_docker_exec(self.docker, self.node["id"], cmd)


class OxtrustExecutor(OxauthExecutor):
    def run_entrypoint(self):
        try:
            # if we already have nginx node in the same provider,
            # add entry to /etc/hosts and import the cert
            node = self.get_nginx_nodes()[0]
            self.add_nginx_host(node)
            if self.node["state"] == STATE_SUCCESS:
                self.import_nginx_cert()
        except IndexError:
            pass

    def get_nginx_nodes(self):
        nodes = self.db.search_from_table(
            "nodes",
            (self.db.where("type") == "nginx")
            & (self.db.where("state") == "SUCCESS")
            & (self.db.where("provider_id") == self.provider["id"]),
        )
        return nodes

    def add_nginx_host(self, node):
        # add the entry only if line is not exist in /etc/hosts
        cmd = "grep -q '^{0} {1}$' /etc/hosts " \
              "|| echo '{0} {1}' >> /etc/hosts" \
            .format(node["weave_ip"],
                    self.cluster["ox_cluster_hostname"])
        result = run_docker_exec(self.docker, self.node["id"], cmd)
        if result.exit_code != 0:
            self.logger.error(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )
            self.docker.stop(self.node["id"])

    def import_nginx_cert(self):
        # imports nginx cert into oxtrust cacerts to avoid
        # "peer not authenticated" error
        cmd = "echo -n | openssl s_client -connect {}:443 | " \
              "sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' " \
              "> /etc/certs/nginx.cert".format(self.cluster["ox_cluster_hostname"])
        result = run_docker_exec(self.docker, self.node["id"], cmd)
        if result.exit_code != 0:
            self.logger.error(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )

            # no need to execute further ops
            return

        cmd = "openssl x509 -outform der -in /etc/certs/nginx.cert -out /etc/certs/nginx.der"
        result = run_docker_exec(self.docker, self.node["id"], cmd)
        if result.exit_code != 0:
            self.logger.error(
                "got error with exit code {} while running docker exec; "
                "reason={}".format(result.exit_code, result.retval)
            )

        cmd = " ".join([
            "keytool -importcert -trustcacerts",
            "-alias '{}'".format(self.cluster["ox_cluster_hostname"]),
            "-file /etc/certs/nginx.der",
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


class OxidpExecutor(OxtrustExecutor):
    def run_entrypoint(self):
        time.sleep(5)
        self.clean_restart_httpd()
        super(OxidpExecutor, self).run_entrypoint()


class NginxExecutor(BaseExecutor):
    pass
