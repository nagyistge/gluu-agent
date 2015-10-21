# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import json

import tinydb
import tinydb.middlewares as tm
import tinydb.storages as ts


class _PatchedTinyDB(tinydb.TinyDB):
    def _read(self):
        return self._storage.read() or {}


class _PatchedJSONStorage(ts.JSONStorage):
    def read(self):
        # Get the file size
        self._handle.seek(0, 2)
        size = self._handle.tell()

        if not size:
            # File is empty
            return None
        else:
            self._handle.seek(0)
            return json.load(self._handle)


class _PatchedSerializationMiddleware(tm.SerializationMiddleware):
    def read(self):
        data = self.storage.read()

        if data is None:
            return None

        for serializer_name in self._serializers:
            serializer = self._serializers[serializer_name]
            tag = '{{{0}}}:'.format(serializer_name)  # E.g: '{TinyDate}:'

            for table_name in data:
                table = data[table_name]

                for eid in table:
                    item = data[table_name][eid]

                    for field in item:
                        try:
                            if item[field].startswith(tag):
                                encoded = item[field][len(tag):]
                                item[field] = serializer.decode(encoded)
                        except AttributeError:
                            pass  # Not a string
        return data


class Database(object):
    def __init__(self, database_uri):
        # self.db = tinydb.TinyDB(*args, **kwargs)

        # use patched database, middleware, and storage to prevent
        # database being written out when JSON is invalid
        # see: https://github.com/msiemens/tinydb/issues/67
        # TODO: remove patches when tinydb v3 is released
        self.db = _PatchedTinyDB(
            database_uri,
            storage=_PatchedSerializationMiddleware(_PatchedJSONStorage),
        )

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
