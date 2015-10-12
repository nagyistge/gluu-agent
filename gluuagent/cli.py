# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import click

from .tasks import RecoveryTask


@click.group()
def main():
    pass


@main.command()
def recover():
    task = RecoveryTask()
    task.execute()
