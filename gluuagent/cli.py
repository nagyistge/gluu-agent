# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import click

from .database import Database
from .tasks import RecoveryTask
from .utils import get_logger


@click.group(context_settings={
    "help_option_names": ["-h", "--help"],
})
def main():
    pass


@main.command()
@click.option(
    "--database",
    default="/var/lib/gluu-cluster/db/db.json",
    help="Path to database file (default to /var/lib/gluu-cluster/db/db.json)",
    metavar="<database>",
    )
@click.option(
    "--logfile",
    default=None,
    help="Path to log file (if omitted will use stdout)",
    metavar="<logfile>",
    )
def recover(database, logfile):
    """Run recovery process.
    """
    db = Database(database)
    logger = get_logger(logfile)
    task = RecoveryTask(db, logger)
    task.execute()
