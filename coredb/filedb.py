#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
from enum import Enum
from pathlib import Path

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
        self._modifiedAfterSaved = False

        if self._filePath.is_file():
            shutil.copy(self._filePath, self._tmpPath)

    @property
    def isModified(self):
        return self._modifiedAfterSaved

    def putBcFile(self, bcid, role, filePath):
        self._saveFile(self._bcKey(bcid, role), Path(filePath), self._columnCounts[role])

    def getBcFile(self, bcid, role):
        return self._loadFile(self._bcKey(bcid, role))

    def getBcFileName(self, bcid, role):
        return self._getFileName(self._bcKey(bcid, role))

    def loadCoreDB(self):
        if coredb.loaded():
            raise AssertionError('Coredb has not been freed for a fresh load.')

        if self._filePath.is_file():
            return coredb.loadDB(self._filePath)

        raise AssertionError('Project configuration file was not found.')

    def saveCoreDB(self):
        if coredb.loaded():
            coredb.CoreDB().save(self._filePath)
        else:
            raise AssertionError('CoreDB has not been created')

    def save(self):
        self._save(self._filePath)

    def saveAs(self, directory):
        self._save(directory / 'configuration.h5')

    def _bcKey(self, bcid, role):
        return f'bc{bcid}{role.value}'

    def _saveFile(self, key, filePath, columnCount):
        df = pd.read_csv(filePath, header=None, index_col=None)
        if len(df.columns) != columnCount:
            raise FileFormatError

        with pd.HDFStore(self._tmpPath) as store:
            store.put(key, df)
            store.get_storer(key).attrs.fileName = filePath.name

        self._modifiedAfterSaved = True

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

    def _save(self, filePath):
        if self._tmpPath.is_file():
            shutil.copy(self._tmpPath, filePath)

        coredb.CoreDB().save(filePath)
        self._modifiedAfterSaved = False
