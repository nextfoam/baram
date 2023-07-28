#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
from openfoam import parallel
from openfoam.dictionary_file import DictionaryFile


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
    def __init__(self, rname: str = ''):
        super().__init__(self.systemLocation(rname), 'decomposeParDict')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        numCores = parallel.getNP()

        self._data = {
            'numberOfSubdomains': numCores,
            'method': MethodType.SCOTCH.value
        }
        return self
