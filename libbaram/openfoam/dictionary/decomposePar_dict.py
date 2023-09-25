#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile


class MethodType(Enum):
    NONE         = 'none'
    MANUAL       = 'manual'
    SIMPLE       = 'simple'
    HIERARCHICAL = 'hierarchical'
    KAHIP        = 'kahip'
    METIS        = 'metis'
    SCOTCH       = 'scotch'
    STRUCTURED   = 'structured'
    MULTILEVEL   = 'multiLevel'


class DecomposeParDict(DictionaryFile):
    def __init__(self, casePath, numCores):
        super().__init__(casePath, self.systemLocation(), 'decomposeParDict')

        self._numCores = numCores
        self._rname = ''

    def setRegion(self, rname):
        self._rname = rname
        self._header['location'] = str(self.systemLocation(rname))

        return self

    def build(self):
        if self._data is not None:
            return self

        self._data = {
            'numberOfSubdomains': self._numCores,
            'method': MethodType.SCOTCH.value
        }

        return self
