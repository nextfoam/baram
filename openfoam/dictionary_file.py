#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from enum import Enum

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator


VERSION = '2.0'


class Format(Enum):
    FORMAT_ASCII = 'ascii'


class DataClass(Enum):
    CLASS_DICTIONARY = 'dictionary'
    CLASS_VOL_SCALAR_FIELD = 'volScalarField'
    CLASS_VOL_VECTOR_FIELD = 'volVectorField'


class DictionaryFile:
    CONSTANT_DIRECTORY_NAME = 'constant'
    BOUNDARY_DIRECTORY_NAME = '0'
    SYSTEM_DIRECTORY_NAME = 'system'
    POLYMESH_DIRECTORY_NAME = 'polymesh'

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
        return os.path.join(cls.CONSTANT_DIRECTORY_NAME, subPath) if subPath else cls.CONSTANT_DIRECTORY_NAME

    @classmethod
    def boundaryLocation(cls, subPath=None):
        return os.path.join(cls.BOUNDARY_DIRECTORY_NAME, subPath) if subPath else cls.BOUNDARY_DIRECTORY_NAME

    @classmethod
    def systemLocation(cls, subPath=None):
        return os.path.join(cls.SYSTEM_DIRECTORY_NAME, subPath) if subPath else cls.SYSTEM_DIRECTORY_NAME

    @classmethod
    def polyMeshLocation(cls, rname=None):
        return os.path.join(cls.CONSTANT_DIRECTORY_NAME, rname, cls.POLYMESH_DIRECTORY_NAME) if rname else \
            cls.constantLocation(cls.POLYMESH_DIRECTORY_NAME)

    def fullPath(self, casePath):
        return os.path.join(casePath, self._header["location"], self._header["object"])

    def asDict(self):
        return self._data

    def write(self, casePath):
        if self._data:
            with open(self.fullPath(casePath), 'w') as f:
                f.write(str(FoamFileGenerator(self._data, header=self._header)))

    def _setFormat(self, fileFormat: Format):
        self._header['format'] = fileFormat.value

    def _setClass(self, dataClass: DataClass):
        self._header['class'] = dataClass.value
