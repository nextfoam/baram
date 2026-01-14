#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
from enum import Enum
from pathlib import Path

import pandas as pd
import h5py

from baramFlow.coredb import coredb


class BcFileRole(Enum):
    BC_VELOCITY_COMPONENT = 'VelocityComponent'
    BC_VELOCITY_MAGNITUDE = 'VelocityMagnitude'
    BC_TEMPERATURE = 'Temperature'
    BC_FAN_CURVE = 'FanCurve'


class FileFormatError(Exception):
    pass


class FileDB:
    class Key(Enum):
        BATCH_CASES = 'BatchCases'
        SNAPSHOT_CASES = 'SnapshotCases'

    FILE_NAME = 'configuration.h5'

    _columnCounts = {
        BcFileRole.BC_VELOCITY_COMPONENT: 6,
        BcFileRole.BC_VELOCITY_MAGNITUDE: 4,
        BcFileRole.BC_TEMPERATURE: 4,
        BcFileRole.BC_FAN_CURVE: 0
    }

    def __init__(self, projectPath):
        self._filePath = projectPath / self.FILE_NAME
        self._tmpPath = projectPath / 'configuration'
        self._modifiedAfterSaved = False

        if self._filePath.is_file():
            shutil.copy(self._filePath, self._tmpPath)

    @property
    def isModified(self):
        return self._modifiedAfterSaved

    def putBcFile(self, bcid, role, filePath):
        return self._saveFile(self._bcKey(bcid, role), Path(filePath), self._columnCounts[role])

    def getFileContents(self, key):
        if key:
            with pd.HDFStore(self._tmpPath) as store:
                if f'/{key}' in store.keys():
                    return store.get(key)
                else:
                    return None

    def getUserFileName(self, key):
        if key:
            with pd.HDFStore(self._tmpPath) as store:
                if f'/{key}' in store.keys():
                    return store.get_storer(key).attrs.fileName
                else:
                    return None

    def putText(self, key, data):
        with h5py.File(self._tmpPath, 'a') as f:
            if key in f.keys():
                del f[key]
            f[key] = data

        self._modifiedAfterSaved = True

    def getText(self, key):
        try:
            with h5py.File(self._tmpPath, 'r') as f:
                ds = f[key]
                return ds[()]
        except KeyError:
            return None

    def putDataFrame(self, name, df):
        with pd.HDFStore(self._tmpPath) as store:
            store.put(name, df)

        self._modifiedAfterSaved = True

    def getDataFrame(self, name):
        with pd.HDFStore(self._tmpPath) as store:
            if f'/{name}' in store.keys():
                return store.get(name)
            else:
                return None

    def loadCoreDB(self):
        if coredb.loaded():
            raise AssertionError('Coredb has not been freed for a fresh load.')

        if self._filePath.is_file():
            return coredb.loadDB(self._filePath)

        raise FileNotFoundError

    def saveCoreDB(self):
        if coredb.loaded():
            coredb.CoreDB().save(self._filePath)
            shutil.copy(self._filePath, self._tmpPath)
        else:
            raise AssertionError('CoreDB has not been created')

    def save(self):
        self._save(self._filePath)

    def saveAs(self, directory):
        self._save(directory / 'configuration.h5')
        self._modifiedAfterSaved = False

    def delete(self, key):
        if key:
            path = f'/{key}'
            with pd.HDFStore(self._tmpPath) as store:
                if path in store.keys():
                    del store[path]

            self._modifiedAfterSaved = True

    @classmethod
    def exists(cls, path):
        dbPath = path / cls.FILE_NAME

        return dbPath.is_file()

    def _bcKey(self, bcid, role):
        return f'bc{bcid}{role.value}'

    def _uniqKey(self, newKey, keys):
        key = newKey
        i = 1

        while f'/{key}' in keys:
            key = f'{newKey}_{i}'
            i += 1

        return key

    def _saveFile(self, key, filePath, columnCount):
        df = pd.read_csv(filePath, header=None, index_col=None)
        if columnCount and len(df.columns) != columnCount:
            raise FileFormatError

        with pd.HDFStore(self._tmpPath) as store:
            key = self._uniqKey(key, store.keys())
            store.put(key, df)
            store.get_storer(key).attrs.fileName = filePath.name

        self._modifiedAfterSaved = True

        return key

    def _save(self, filePath):
        if self._tmpPath.is_file():
            shutil.copy(self._tmpPath, filePath)

        coredb.CoreDB().save(filePath)
        self._modifiedAfterSaved = False
