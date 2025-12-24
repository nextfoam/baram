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
    def __init__(self, casePath,  rname: str = '', numCores: int = 1, singleProcessorFaceSets: list[str]=[]):
        super().__init__(casePath, self.systemLocation(rname), 'decomposeParDict')

        self._numCores = numCores
        self._rname = ''

        self._singleProcessorFaceSets = singleProcessorFaceSets

    def build(self):
        if self._data is not None:
            return self

        self._data = {
            'numberOfSubdomains': self._numCores,
            'method': MethodType.SCOTCH.value
        }

        if self._singleProcessorFaceSets:
            self._data.update({
                'constraints': {
                    'processors': {
                        'type': 'singleProcessorFaceSets',
                        'sets': [[s, '-1'] for s in self._singleProcessorFaceSets],
                        'enabled': 'true',
                    }
                }
            })

        return self
