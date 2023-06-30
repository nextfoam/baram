#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

import yaml

from .schema import Schema, SchemaList


class SimpleDB(Schema):
    def __init__(self, schema, editable=False):
        super().__init__(schema)
        self._db = None
        self._editable = editable
        self._modified = False
        self._base = ''

    def isModified(self):
        return self._modified

    def createData(self):
        self._db = self.generateData()

    def data(self):
        return self._db

    def checkout(self, path=''):
        """ Creates and returns a SimpleDB replicated with the original's subdata.

        :param path: The root path to clone.
        :return: New SimpleDB based on specific path.
        """
        subSchema = self._schema
        subDB = self._db
        if path != self._base:
            schema, db, key = self._get(path)
            subSchema = schema[key]
            subDB = db[key]

        subData = SimpleDB(subSchema)
        subData._db = copy.deepcopy(subDB)
        subData._editable = True
        subData._base = f'{self._base}/{path}' if self._base else path

        return subData

    def commit(self, data):
        """ Replaces part of the data

        :param data: SimpleDB based on the root path of the data to be replaced
        """
        if not data._base.startswith(self._base):
            raise LookupError

        if not data._modified or not data._editable:
            return

        if data._base == self._base:
            self._db = data._db
        else:
            path = data._base[len(self._base) + 1:]
            schema, db, key = self._get(path)
            db[key] = data._db

        data._modified = False
        self._modified = True

    def getValue(self, path):
        schema, db, key = self._get(path)
        if isinstance(db[key], dict):
            raise LookupError

        return db[key]

    def getFloat(self, path):
        return float(self.getValue(path))

    def getVector(self, path):
        schema, db, key = self._get(path)
        if not isinstance(db[key], dict):
            raise LookupError

        return db[key]['x'], db[key]['y'], db[key]['z']

    def setValue(self, path, value, name=None):
        if not self._editable:
            raise LookupError

        schema, db, key = self._get(path)
        value = schema[key].validate(value, name)
        if db[key] != value:
            db[key] = value
            self._modified = True

            return True

        return False

    def newElement(self, path):
        schema, _, key = self._get(path)

        schema = schema[key]
        if not isinstance(schema, SchemaList):
            raise TypeError

        db = SimpleDB(schema.elementSchema().schema(), True)
        db.createData()

        return db

    def addElement(self, path, newdb, index=None):
        if not self._editable:
            raise LookupError

        schema, db, key = self._get(path)

        schema = schema[key]
        if not isinstance(schema, SchemaList):
            raise TypeError

        index = schema.index(index, db[key])
        if index in db[key]:
            raise KeyError

        if schema.elementSchema().schema() == newdb._schema:
            db[key][index] = schema.elementSchema().validateElement(newdb)
        else:
            raise TypeError

        self._modified = True

        return index

    def getElement(self, path, idx, columns=None):
        schema, db, key = self._get(path)

        schema = schema[key]
        if not isinstance(schema, SchemaList):
            raise TypeError

        if idx not in db[key]:
            raise LookupError

        if columns is None:
            return copy.deepcopy(db[key][idx])

        return {k: copy.deepcopy(db[key][idx][k]) for k in columns}

    def getElements(self, path, columns=None):
        schema, db, key = self._get(path)

        schema = schema[key]
        if not isinstance(schema, SchemaList):
            raise TypeError

        if columns is None:
            return copy.deepcopy(db[key])

        return {idx: {k: copy.deepcopy(db[key][idx][k]) for k in columns} for idx in db[key]}

    def getFilteredElements(self, path, function, columns=None):
        schema, db, key = self._get(path)

        schema = schema[key]
        if not isinstance(schema, SchemaList):
            raise TypeError

        elements = dict(filter(lambda elem: function(elem[0], elem[1]), db[key].items()))
        if columns is None:
            return copy.deepcopy(elements)

        return {idx: {k: copy.deepcopy(db[key][idx][k]) for k in columns} for idx in elements}

    def removeElement(self, path, index):
        if not self._editable:
            raise LookupError

        schema, db, key = self._get(path)

        schema = schema[key]
        if not isinstance(schema, SchemaList):
            raise TypeError

        if index not in db[key]:
            raise KeyError

        del db[key][index]

        self._modified = True

    def toYaml(self):
        return yaml.dump(self._db)

    def loadYaml(self, data, fillWithDefault=False):
        self._db = self.validateData(yaml.full_load(data), fillWithDefault=fillWithDefault)

    def _get(self, path):
        keys = path.split('/')
        schema = self._schema
        data = self._db

        depth = len(keys) - 1
        for i in range(depth):
            schema = schema[keys[i]]
            data = data[keys[i]]

        return schema, data, keys[depth]
