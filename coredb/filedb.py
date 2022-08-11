#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from enum import Enum

import pandas as pd

from coredb import coredb


class BcFileRole(Enum):
    BC_VELOCITY_COMPONENT = 'VelocityComponent'
    BC_VELOCITY_MAGNITUDE = 'VelocityMagnitude'
    BC_TEMPERATURE = 'Temperature'


class FileFormatError(Exception):
    pass


class FileDB:
    _columnCounts = {
        BcFileRole.BC_VELOCITY_COMPONENT: 6,
        BcFileRole.BC_VELOCITY_MAGNITUDE: 4,
        BcFileRole.BC_TEMPERATURE: 4,
    }

    def __init__(self, projectPath):
        self._filePath = projectPath / 'configuration.h5'
        self._tmpPath = projectPath / 'configuration'
        self._modificationCount = 0
        self._modificationCountAtSave = 0

        if os.path.isfile(self._filePath):
            shutil.copy(self._filePath, self._tmpPath)

    @property
    def isModified(self):
        return self._modificationCountAtSave != self._modificationCount

    def putBcFile(self, bcid, role, filePath):
        self._saveFile(self._bcKey(bcid, role), filePath, self._columnCounts[role])

    def getBcFile(self, bcid, role):
        return self._loadFile(self._bcKey(bcid, role))

    def getBcFileName(self, bcid, role):
        return self._getFileName(self._bcKey(bcid, role))

    def load(self):
        coreDB = coredb.CoreDB()
        if os.path.isfile(self._filePath):
            coreDB.load(self._filePath)

        self._modificationCountAtSave = self._modificationCount

        return coreDB

    def save(self, coreDB):
        if os.path.isfile(self._tmpPath):
            shutil.copy(self._tmpPath, self._filePath)

        coreDB.save(self._filePath)

        self._modificationCountAtSave = self._modificationCount

    def saveAs(self, coreDB, directory):
        filePath = os.path.join(directory, 'configuration.h5')

        if os.path.isfile(self._tmpPath):
            shutil.copy(self._tmpPath, filePath)

        coreDB.save(filePath)

        self._modificationCountAtSave = self._modificationCount

    def _bcKey(self, bcid, role):
        return f'bc{bcid}{role.value}'

    def _saveFile(self, key, filePath, columnCount):
        df = pd.read_csv(filePath, header=None, index_col=None)
        if len(df.columns) != columnCount:
            raise FileFormatError

        with pd.HDFStore(self._tmpPath) as store:
            store.put(key, df)
            store.get_storer(key).attrs.fileName = os.path.basename(filePath)

        self._modificationCount += 1

    def _loadFile(self, key):
        with pd.HDFStore(self._tmpPath) as store:
            if f'/{key}' in store.keys():
                return store.get(key)
            else:
                return None

    def _getFileName(self, key):
        with pd.HDFStore(self._tmpPath) as store:
            if f'/{key}' in store.keys():
                return store.get_storer(key).attrs.fileName
            else:
                return None
