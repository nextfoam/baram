#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramMesh.app import app


@dataclass
class SurfacePatchData:
    fileName: str
    featureAngle: str


class SurfacePatchDict(DictionaryFile):
    def __init__(self):
        super().__init__(app.fileSystem.caseRoot(), self.systemLocation(), 'surfacePatchDict')

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
