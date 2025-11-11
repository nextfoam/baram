#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
import tempfile
from pathlib import Path

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from libbaram.openfoam.constants import Directory

from resources import resource


VERSION = '2.0'


class Format(Enum):
    FORMAT_ASCII = 'ascii'


class DataClass(Enum):
    CLASS_DICTIONARY = 'dictionary'
    CLASS_VOL_SCALAR_FIELD = 'volScalarField'
    CLASS_VOL_VECTOR_FIELD = 'volVectorField'
    CLASS_VECTOR_FIELD = 'vectorField'


class DictionaryFile:
    def __init__(self, casePath, location, objectName,
                 class_=DataClass.CLASS_DICTIONARY, format_=Format.FORMAT_ASCII, data=None):
        self._header = {
            'version': VERSION,
            'format': format_.value,
            'class': class_.value,
            'location': str(location),
            'object': objectName
        }
        self._data = data
        self._casePath = casePath

    def isBuilt(self):
        return self._data is not None

    def constantLocation(cls, subPath=''):
        return Path(Directory.CONSTANT_DIRECTORY_NAME) / subPath

    def boundaryLocation(cls, rname, time):
        return Path(time) / rname

    def systemLocation(cls, subPath=''):
        return Path(Directory.SYSTEM_DIRECTORY_NAME) / subPath

    def polyMeshLocation(cls, rname=''):
        return Path(Directory.CONSTANT_DIRECTORY_NAME) / rname / Directory.POLY_MESH_DIRECTORY_NAME

    def fullPath(self, processorNo=None) -> Path:
        processorDir = '' if processorNo is None else f'processor{processorNo}'
        return self._casePath / processorDir / self._header['location'] / self._header['object']

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
        path = self.fullPath(processorNo)
        if self._data:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                f.write(str(FoamFileGenerator(self._data, header=self._header)))
        else:
            path.unlink(missing_ok=True)

    def _boolToYN(self, bool):
        return 'yes' if bool else 'no'
