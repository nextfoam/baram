#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

import yaml

from .schema import ErrorType, ConfigError


class SimpleDB:
    def __init__(self, schema):
        self._schema = schema
        self._db = None
        self._editable = False
        self._modified = False
        self._base = ''

    def isModified(self):
        return self._modified

    def createData(self):
        self._db = self._generateData(self._schema)

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

        if not data._modified:
            return

        if data._base == self._base:
            self._db = data._db
        else:
            path = data._base[len(self._base) + 1:]
            schema, db, key = self._get(path)
            db[key] = data._db

        self._modified = data._modified

    def getValue(self, path):
        schema, db, key = self._get(path)
        if isinstance(db[key], dict):
            raise LookupError

        return db[key]

    def getFloat(self, path):
        return float(self.getValue(path))

    def setValue(self, path, value, name=None):
        if not self._editable:
            raise LookupError('Not editable')

        schema, db, key = self._get(path)
        value = schema[key].validate(value, name)
        if db[key] != value:
            db[key] = value
            self._modified = True

    def toYaml(self):
        return yaml.dump(self._db)

    def loadYaml(self, data):
        self._db = self._validateData(yaml.full_load(data), self._schema)

    def _generateData(self, schema):
        configuration = {}
        for key in schema:
            if isinstance(schema[key], dict):
                configuration[key] = self._generateData(schema[key])
            else:
                configuration[key] = schema[key].default()

        return configuration

    def _validateData(self, data, schema, path=''):
        configuration = {}
        for key in schema:
            path = f'{path}/{key}'
            if isinstance(schema[key], dict):
                configuration[key] = self._validateData(data[key], schema[key], path)
            else:
                try:
                    configuration[key] = schema[key].validate(data[key])
                except ConfigError as ce:
                    ce.setPath(path)
                    raise ce
                except KeyError as ke:
                    raise ConfigError(ErrorType.EmptyError, repr(ke), None, path)

        return configuration

    def _get(self, path):
        keys = path.split('/')
        schema = self._schema
        data = self._db

        depth = len(keys) - 1
        for i in range(depth):
            schema = schema[keys[i]]
            data = data[keys[i]]

        return schema, data, keys[depth]
