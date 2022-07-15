#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pandas as pd
from enum import Enum

from .settings import Settings


class BcFileRole(Enum):
    BC_VELOCITY_COMPONENT = 'VelocityComponent'
    BC_VELOCITY_MAGNITUDE = 'VelocityMagnitude'
    BC_TEMPERATURE = 'Temperature'


class FileFormatError(Exception):
    pass


class FileDB:
    columnCounts = {
        BcFileRole.BC_VELOCITY_COMPONENT: 6,
        BcFileRole.BC_VELOCITY_MAGNITUDE: 4,
        BcFileRole.BC_TEMPERATURE: 4,
    }

    @classmethod
    def putBcFile(cls, bcid, role, filePath):
        cls._save(cls._bcKey(bcid, role), filePath, cls.columnCounts[role])

    @classmethod
    def getBcFile(cls, bcid, role):
        return cls._load(cls._bcKey(bcid, role))

    @classmethod
    def getBcFileName(cls, bcid, role):
        return cls._getFileName(cls._bcKey(bcid, role))

    @classmethod
    def _filePath(cls):
        return os.path.join(Settings.settingsDirectory(), 'files.h5')

    @classmethod
    def _bcKey(cls, bcid, role):
        return f'bc{bcid}{role.value}'

    @classmethod
    def _save(cls, key, filePath, columnCount):
        df = pd.read_csv(filePath, header=None, index_col=None)
        if len(df.columns) != columnCount:
            raise FileFormatError

        with pd.HDFStore(cls._filePath()) as store:
            store.put(key, df)
            store.get_storer(key).attrs.fileName = os.path.basename(filePath)

    @classmethod
    def _load(cls, key):
        with pd.HDFStore(cls._filePath()) as store:
            if f'/{key}' in store.keys():
                return store.get(key)
            else:
                return None

    @classmethod
    def _getFileName(cls, key):
        with pd.HDFStore(cls._filePath()) as store:
            if f'/{key}' in store.keys():
                return store.get_storer(key).attrs.fileName
            else:
                return None
