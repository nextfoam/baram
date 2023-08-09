#!/usr/bin/env python
# -*- coding: utf-8 -*-

from openfoam.dictionary_file import DictionaryFile


class RefineMeshDict(DictionaryFile):
    def __init__(self):
        super().__init__(self.systemLocation(), 'refineMeshDict')

    def build(self, name):
        if self._data is not None:
            return self

        self._data = {
            'set': name,
            'coordinateSystem': 'global',
            'globalCoeffs': {
                'tan1': [1, 0, 0],
                'tan2': [0, 1, 0]
            },
            'directions': [
                'tan1', 'tan2', 'normal'
            ],
            'useHexTopology': 'true',
            'geometricCut': 'false',
            'writeMesh': 'false'
        }

        return self
