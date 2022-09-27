#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from enum import Enum
import tempfile
from pathlib import Path

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from .file_system import FileSystem


VERSION = '2.0'


class Format(Enum):
    FORMAT_ASCII = 'ascii'


class DataClass(Enum):
    CLASS_DICTIONARY = 'dictionary'
    CLASS_VOL_SCALAR_FIELD = 'volScalarField'
    CLASS_VOL_VECTOR_FIELD = 'volVectorField'


class DictionaryFile:
    def __init__(self, location, objectName, class_=DataClass.CLASS_DICTIONARY, format_=Format.FORMAT_ASCII):
        self._header = {
            'version': VERSION,
            'format': format_.value,
            'class': class_.value,
            'location': location,
            'object': objectName
        }
        self._data = None

    @classmethod
    def constantLocation(cls, subPath=None):
        return os.path.join(FileSystem.CONSTANT_DIRECTORY_NAME, subPath) if subPath else\
            FileSystem.CONSTANT_DIRECTORY_NAME

    @classmethod
    def boundaryLocation(cls, subPath=None):
        return os.path.join(FileSystem.BOUNDARY_CONDITIONS_DIRECTORY_NAME, subPath) if subPath else\
            FileSystem.BOUNDARY_CONDITIONS_DIRECTORY_NAME

    @classmethod
    def systemLocation(cls, subPath=None):
        return os.path.join(FileSystem.SYSTEM_DIRECTORY_NAME, subPath) if subPath else\
            FileSystem.SYSTEM_DIRECTORY_NAME

    @classmethod
    def polyMeshLocation(cls, rname=None):
        return os.path.join(FileSystem.CONSTANT_DIRECTORY_NAME, rname, FileSystem.POLY_MESH_DIRECTORY_NAME)\
            if rname else cls.constantLocation(FileSystem.POLY_MESH_DIRECTORY_NAME)

    def fullPath(self):
        return FileSystem.caseRoot() / self._header["location"] / self._header["object"]

    def asDict(self):
        return self._data

    def write(self):
        if self._data:
            with open(self.fullPath(), 'w') as f:
                f.write(str(FoamFileGenerator(self._data, header=self._header)))

    def writeAtomic(self):
        if self._data:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=self.fullPath().parent) as f:
                f.write(str(FoamFileGenerator(self._data, header=self._header)))
                p = Path(f.name)
            p.replace(self.fullPath())

    def _setFormat(self, fileFormat: Format):
        self._header['format'] = fileFormat.value

    def _setClass(self, dataClass: DataClass):
        self._header['class'] = dataClass.value
