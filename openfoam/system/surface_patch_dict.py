#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from openfoam.dictionary_file import DictionaryFile


@dataclass
class SurfacePatchData:
    fileName: str
    featureAngle: str


class SurfacePatchDict(DictionaryFile):
    def __init__(self):
        super().__init__()
        self._setHeader(self.systemLocation(), 'surfacePatchDict')

    def build(self, data):
        if self._data is not None:
            return self

        self._data = {
            'geometry': {
                data.fileName: {
                    'type': 'triSurfaceMesh'
                }
            },
            'surfaces': {
                data.fileName: {
                    'type': 'autoPatch',
                    'featureAngle': data.featureAngle
                }
            }
        }

        return self
