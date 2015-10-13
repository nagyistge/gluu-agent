# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.


import os
import tinydb


DEFAULT_DATABASE_URI = "/var/lib/gluu-cluster/db/db.json"


class Database(object):
    def __init__(self):
        filepath = os.environ.get("DATABASE_URI", DEFAULT_DATABASE_URI)
        self.db = tinydb.TinyDB(filepath)

        # shortcut to ``tinydb.where``
        self.where = tinydb.where

    def get(self, identifier, table_name):
        table = self.db.table(table_name)
        data = table.get(self.where("id") == identifier)
        return data

    def all(self, table_name):
        table = self.db.table(table_name)
        data = table.all()
        return data

    def search_from_table(self, table_name, condition):
        table = self.db.table(table_name)
        data = table.search(condition)
        return data

    def count_from_table(self, table_name, condition):
        table = self.db.table(table_name)
        return table.count(condition)
