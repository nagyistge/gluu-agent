# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import tinydb


class Database(object):
    def __init__(self, *args, **kwargs):
        self.db = tinydb.TinyDB(*args, **kwargs)

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
