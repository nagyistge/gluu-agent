# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

STATE_DISABLED = "DISABLED"

STATE_SUCCESS = "SUCCESS"

RECOVERY_PRIORITY_CHOICES = {
    "ldap": 1,
    "oxauth": 2,
    "oxidp": 3,
    "httpd": 4,
    "nginx": 4,
    "oxtrust": 5,
}
