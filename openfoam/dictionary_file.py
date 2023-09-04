#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
import tempfile
from pathlib import Path

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from app import app
from resources import resource


VERSION = '2.0'


class Format(Enum):
    FORMAT_ASCII = 'ascii'


class DataClass(Enum):
    CLASS_DICTIONARY = 'dictionary'
    CLASS_VOL_SCALAR_FIELD = 'volScalarField'
    CLASS_VOL_VECTOR_FIELD = 'volVectorField'


class DictionaryFile:
    def __init__(self, fileSystem=None):
        self._fileSystem = fileSystem if fileSystem else app.fileSystem
        self._header = None
        self._data = None

    def isBuilt(self):
        return self._data is not None

    def constantLocation(self, subPath=''):
        return Path(self._fileSystem.CONSTANT_DIRECTORY_NAME) / subPath

    @classmethod
    def boundaryLocation(cls, rname, time):
        return Path(time) / rname

    def systemLocation(self, subPath=''):
        return Path(self._fileSystem.SYSTEM_DIRECTORY_NAME) / subPath

    def polyMeshLocation(self, rname=''):
        return Path(self._fileSystem.CONSTANT_DIRECTORY_NAME) / rname / self._fileSystem.POLY_MESH_DIRECTORY_NAME

    def fullPath(self, rname=None):
        if rname:
            return self._fileSystem.caseRoot() / self._header['location'] / rname / self._header['object']
        else:
            return self._fileSystem.caseRoot() / self._header['location'] / self._header['object']

    def asDict(self):
        return self._data

    def write(self):
        self._write()

    def writeAtomic(self):
        if self._data:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=self.fullPath().parent) as f:
                f.write(str(FoamFileGenerator(self._data, header=self._header)))
                p = Path(f.name)
            p.replace(self.fullPath())

    def writeByRegion(self, rname):
        self._write(rname)

    def copyFromResource(self, src):
        resource.copy(src, self.fullPath())

    def _setHeader(self, location, objectName, class_=DataClass.CLASS_DICTIONARY, format_=Format.FORMAT_ASCII):
        self._header = {
            'version': VERSION,
            'format': format_.value,
            'class': class_.value,
            'location': str(location),
            'object': objectName
        }

    def _write(self, rname=None):
        if self._data:
            with open(self.fullPath(rname), 'w') as f:
                f.write(str(FoamFileGenerator(self._data, header=self._header)))
