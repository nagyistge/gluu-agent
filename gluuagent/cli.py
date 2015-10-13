# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import click

from .database import Database
from .tasks import RecoveryTask
from .utils import get_logger


@click.group()
def main():
    pass


@main.command()
@click.option(
    "--database",
    default="/var/lib/gluu-cluster/db.json",
    help="Path to database file (default to /var/lib/gluu-cluster/db.json)",
    metavar="<database>",
    )
@click.option(
    "--logfile",
    default="/var/log/gluuagent-recover.log",
    help="Path to database file (default to /var/log/gluuagent-recover.log)",
    metavar="<logfile>",
    )
def recover(database, logfile):
    db = Database(database)
    logger = get_logger(logfile)
    task = RecoveryTask(db, logger)
    task.execute()
