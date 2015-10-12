# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import base64
import logging
import logging.handlers

from M2Crypto.EVP import Cipher
from netaddr import IPNetwork


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


def decrypt_text(encrypted_text, key):
    # Porting from pyDes-based encryption (see http://git.io/htpk)
    # to use M2Crypto instead (see https://gist.github.com/mrluanma/917014)
    cipher = Cipher(alg="des_ede3_ecb",
                    key=b"{}".format(key),
                    op=0,
                    iv="\0" * 16)
    decrypted_text = cipher.update(
        base64.b64decode(b"{}".format(encrypted_text))
    )
    decrypted_text += cipher.final()
    return decrypted_text


def exposed_weave_ip(weave_ip_network):
    pool = IPNetwork(weave_ip_network)
    # as the last element of pool is a broadcast address, we cannot use it;
    # hence we fetch the last element before broadcast address
    addr = pool[-2]
    return str(addr), pool.prefixlen
