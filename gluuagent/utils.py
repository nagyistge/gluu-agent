# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import logging
import logging.handlers


def get_logger(logfile=None, name=None):
    logger = logging.getLogger(name or "gluu-agent")
    logger.setLevel(logging.INFO)

    if not logfile:
        ch = logging.StreamHandler()
    else:
        ch = logging.handlers.TimedRotatingFileHandler(logfile, when="d")
    fmt = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger
