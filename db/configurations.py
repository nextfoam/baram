#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .simple_db import SimpleDB
from .file_db import FileDB
from .configurations_schema import schema


DB_KEY = 'configurations'


class Configurations(SimpleDB):
    def __init__(self, path):
        super().__init__(schema)

        self._fileDB = FileDB(path)

    def load(self):
        if self._fileDB.exists() and (data := self._fileDB.getText(DB_KEY)):
            self.loadYaml(data, fillWithDefault=True)
        else:
            self.createData()
            self._modified = True

    def save(self):
        if self.isModified():
            self._fileDB.putText(DB_KEY, self.toYaml())
            self._modified = False

        self._fileDB.save()
