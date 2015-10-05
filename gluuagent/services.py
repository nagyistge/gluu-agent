# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import os
import time
import subprocess

from .utils import get_logger


class MinionService(object):
    def __init__(self, pidfile="/var/run/salt-minion.pid", logger=None):
        self.pidfile = pidfile
        self.logger = logger or get_logger()

    def get_pid(self):
        pid = None
        try:
            with open(self.pidfile) as fp:
                pid = int(fp.read())
            self.logger.info("got minion with PID {}".format(pid))
        except IOError as exc:
            self.logger.error(exc)
        return pid

    def is_alive(self, pid):
        try:
            proc = os.getpgid(pid)
        except OSError:
            proc = None
        return proc is not None

    def restart(self):
        restarted = False
        try:
            cmd = subprocess.check_output(
                "service salt-minion restart",
                stderr=subprocess.STDOUT,
                shell=True,
            )
            self.logger.info(cmd)
            restarted = True
        except subprocess.CalledProcessError as exc:
            self.logger.error(exc)
            self.logger.error(exc.output)
        return restarted

    def run_forever(self):
        while True:
            self.logger.info("checking minion PID")

            minion_pid = self.get_pid()
            if not minion_pid:
                time.sleep(60)
                continue

            self.logger.info("checking minion process")
            if self.is_alive(minion_pid):
                self.logger.info("minion is ready")
            else:
                self.logger.warn("minion is not ready yet")
                self.logger.info("(re)starting salt-minion")
                self.restart()
            time.sleep(60)
