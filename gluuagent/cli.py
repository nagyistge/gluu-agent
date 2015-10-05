# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import click
from daemonocle import Daemon

from .services import MinionService
from .utils import get_logger


class GluuAgentCLI(click.MultiCommand):
    def __init__(self, **attrs):
        attrs["callback"] = None
        context_settings = {"obj": Daemon}
        super(GluuAgentCLI, self).__init__(
            context_settings=context_settings,
            **attrs
        )

    def list_commands(self, ctx):
        daemon = ctx.obj()
        return daemon.list_actions()

    def get_command(self, ctx, name):
        if name not in ctx.obj.list_actions():
            return

        logger = get_logger(ctx.params.get("logfile"))
        service = MinionService(logger=logger)
        daemon = ctx.obj(pidfile=ctx.params.get("pidfile"),
                         worker=service.run_forever,
                         )

        def subcommand(debug=False):
            if daemon.detach and debug:
                daemon.detach = False
                # replaces existing logger with new logger
                # that uses StreamHandler
                service.logger = get_logger()
            daemon.do_action(name)

        subcommand.__doc__ = daemon.get_action(name).__doc__

        if name == "start":
            # Add a --debug option for start
            subcommand = click.option(
                "--debug", is_flag=True,
                help="Do NOT detach and run in the background.",
            )(subcommand)

        cmd = click.command(name)(subcommand)
        return cmd


@click.command(cls=GluuAgentCLI)
@click.option(
    "--logfile",
    default="/var/log/gluu-agent.log",
    metavar="<logfile>",
    help="Path to log file (default to /var/log/gluu-agent.log).",
)
@click.option(
    "--pidfile",
    default="/var/run/gluu-agent.pid",
    metavar="<pidfile>",
    help="Path to PID file (default to /var/run/gluu-agent.pid).",
)
@click.pass_context
def main(ctx, logfile, pidfile):
    pass
