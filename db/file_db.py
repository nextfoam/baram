#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil

import h5py


class FileDB:
    def __init__(self, projectPath):
        self._filePath = projectPath / 'configuration.h5'
        self._tmpPath = projectPath / 'configuration'
        self._modifiedAfterSaved = False

        if self._filePath.is_file():
            shutil.copy(self._filePath, self._tmpPath)

    def isModified(self):
        return self._modifiedAfterSaved

    def exists(self):
        return self._filePath.is_file()

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

    def save(self):
        self._save(self._filePath)

    def saveAs(self, directory):
        self._save(directory / 'configuration.h5')
        self._modifiedAfterSaved = False

    def _save(self, filePath):
        if self._tmpPath.is_file():
            shutil.copy(self._tmpPath, filePath)

        self._modifiedAfterSaved = False
