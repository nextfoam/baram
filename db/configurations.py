#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml

from .file_db import writeConfigurations, readConfigurations, FileGroup, newFiles
from .simple_db import SimpleDB
from .migrate import migrate


FILE_NAME = 'configurations.h5'
DB_KEY = 'configurations'


class Configurations(SimpleDB):
    _geometryNextKey = 0

    def __init__(self, schema):
        super().__init__(schema)

        self._path = None
        self._files = newFiles()

    def load(self, path):
        self._path = path / FILE_NAME
        if self._path.exists():
            data, files, maxIds = readConfigurations(self._path)
            self._db = self.validateData(migrate(yaml.full_load(data)), fillWithDefault=True)
            self._files = files
            Configurations._geometryNextKey = maxIds[FileGroup.GEOMETRY_POLY_DATA.value]
        else:
            self.createData()

    def save(self):
        if self.isModified():
            writeConfigurations(self._path, self.toYaml(), self._files)

    def addGeometryPolyData(self, pd):
        Configurations._geometryNextKey += 1
        key = f'Geometry{Configurations._geometryNextKey}'

        self._files['geometry'][key] = pd
        self._modified = True

        return key

    def removeGeometryPolyData(self, key):
        self._files['geometry'][key] = None

    def geometryPolyData(self, key):
        return self._files['geometry'][key]

    def commit(self, data):
        for key in data._files:
            self._files[key].update(data._files[key])

        super().commit(data)

    def _newDB(self, schema, editable=False):
        db = Configurations(schema)
        db._editable = editable

        return db
