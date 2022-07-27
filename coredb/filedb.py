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
    _filePath = None
    _tmpPath = None
    _columnCounts = {
        BcFileRole.BC_VELOCITY_COMPONENT: 6,
        BcFileRole.BC_VELOCITY_MAGNITUDE: 4,
        BcFileRole.BC_TEMPERATURE: 4,
    }

    @classmethod
    def initFilePath(cls, projectDirectory):
        cls._filePath = os.path.join(projectDirectory, 'configuration.h5')
        cls._tmpPath = os.path.join(projectDirectory, 'configuration')

        if os.path.isfile(cls._filePath):
            shutil.copy(cls._filePath, cls._tmpPath)

        return cls._filePath

    @classmethod
    def putBcFile(cls, bcid, role, filePath):
        cls._saveFile(cls._bcKey(bcid, role), filePath, cls._columnCounts[role])

    @classmethod
    def getBcFile(cls, bcid, role):
        return cls._loadFile(cls._bcKey(bcid, role))

    @classmethod
    def getBcFileName(cls, bcid, role):
        return cls._getFileName(cls._bcKey(bcid, role))

    @classmethod
    def load(cls):
        if os.path.isfile(cls._filePath):
            coredb.CoreDB().load(cls._filePath)

    @classmethod
    def save(cls):
        if os.path.isfile(cls._tmpPath):
            shutil.copy(cls._tmpPath, cls._filePath)

        coredb.CoreDB().save(cls._filePath)

    @classmethod
    def _bcKey(cls, bcid, role):
        return f'bc{bcid}{role.value}'

    @classmethod
    def _saveFile(cls, key, filePath, columnCount):
        df = pd.read_csv(filePath, header=None, index_col=None)
        if len(df.columns) != columnCount:
            raise FileFormatError

        with pd.HDFStore(cls._tmpPath) as store:
            store.put(key, df)
            store.get_storer(key).attrs.fileName = os.path.basename(filePath)

    @classmethod
    def _loadFile(cls, key):
        with pd.HDFStore(cls._tmpPath) as store:
            if f'/{key}' in store.keys():
                return store.get(key)
            else:
                return None

    @classmethod
    def _getFileName(cls, key):
        with pd.HDFStore(cls._tmpPath) as store:
            if f'/{key}' in store.keys():
                return store.get_storer(key).attrs.fileName
            else:
                return None
