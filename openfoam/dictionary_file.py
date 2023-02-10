#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
import tempfile
from pathlib import Path

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from resources import resource
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
            'location': str(location),
            'object': objectName
        }
        self._data = None

    @classmethod
    def constantLocation(cls, subPath=''):
        return Path(FileSystem.CONSTANT_DIRECTORY_NAME) / subPath

    @classmethod
    def boundaryLocation(cls, rname, time):
        return Path(time) / rname if time == '0' else Path(time) / rname / 'boundaryFields'

    @classmethod
    def systemLocation(cls, subPath=''):
        return Path(FileSystem.SYSTEM_DIRECTORY_NAME) / subPath

    @classmethod
    def polyMeshLocation(cls, rname=''):
        return Path(FileSystem.CONSTANT_DIRECTORY_NAME) / rname / FileSystem.POLY_MESH_DIRECTORY_NAME

    def fullPath(self, processorNo=None):
        processorDir = '' if processorNo is None else f'processor{processorNo}'
        return FileSystem.caseRoot() / processorDir / self._header['location'] / self._header['object']

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

    def copyFromResource(self, src):
        resource.copy(src, self.fullPath())

    def _setFormat(self, fileFormat: Format):
        self._header['format'] = fileFormat.value

    def _setClass(self, dataClass: DataClass):
        self._header['class'] = dataClass.value

    def _write(self, processorNo=None):
        if self._data:
            with open(self.fullPath(processorNo), 'w') as f:
                f.write(str(FoamFileGenerator(self._data, header=self._header)))
