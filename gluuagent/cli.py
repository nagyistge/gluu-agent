# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import os.path
import sys

import click

from .database import Database
from .tasks import RecoveryTask
from .tasks import ImageUpdateTask
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
    )
@click.option(
    "--logfile",
    default=None,
    help="Path to log file (if omitted will use stdout)",
    )
@click.option(
    "--encrypted",
    is_flag=True,
    help="Enable weave encryption.",
    )
def recover(database, logfile, encrypted):
    """Run recovery process.
    """
    logger = get_logger(logfile, name="gluuagent.recover")

    # checks if database is exist
    if not os.path.exists(database):
        logger.warn("unable to read database {}; "
                    "skipping recovery process".format(database))
        sys.exit(0)

    db = Database(database)
    task = RecoveryTask(db, logger, encrypted)
    task.execute()


@main.command("update-images")
@click.option(
    "--database",
    default="/var/lib/gluu-cluster/db/db.json",
    help="Path to database file (default to /var/lib/gluu-cluster/db/db.json)",
    )
@click.option(
    "--logfile",
    default=None,
    help="Path to log file (if omitted will use stdout)",
    )
def update_images(database, logfile):
    """Run image update process.
    """
    logger = get_logger(logfile, name="gluuagent.update_image")

    # checks if database is exist
    if not os.path.exists(database):
        logger.warn("unable to read database {}; "
                    "skipping image update process".format(database))
        sys.exit(0)

    db = Database(database)
    task = ImageUpdateTask(db, logger)
    task.execute()
