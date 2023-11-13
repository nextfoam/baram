#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramMesh.app import app
from baramMesh.db.configurations_schema import Shape
from baramMesh.db.simple_db import elementToVector


class BlockMeshDict(DictionaryFile):
    def __init__(self):
        super().__init__(app.fileSystem.caseRoot(), self.systemLocation(), 'blockMeshDict')

    def build(self):
        if self._data is not None:
            return self

        gradingRatio = [1, 1, 1]

        x1, x2, y1, y2, z1, z2 = app.window.geometryManager.getBounds().toTuple()
        bNames = {Shape.X_MIN.value: 'xMin',
                  Shape.X_MAX.value: 'xMax',
                  Shape.Y_MIN.value: 'yMin',
                  Shape.Y_MAX.value: 'yMax',
                  Shape.Z_MIN.value: 'zMin',
                  Shape.Z_MAX.value: 'zMax'}

        cx, cy, cz = app.db.getValues('baseGrid', ['numCellsX', 'numCellsY', 'numCellsZ'])
        padding = min((x2-x1)/int(cx), (y2-y1)/int(cy), (z2-z1)/int(cz)) / 100

        gId, geometry = app.window.geometryManager.getBoundingHex6()
        if geometry is not None:  # boundingHex6 is configured
            x1, y1, z1 = elementToVector(geometry['point1'])
            x2, y2, z2 = elementToVector(geometry['point2'])
            padding = 0

            for sId in app.window.geometryManager.subSurfaces(gId):
                s = app.window.geometryManager.geometry(sId)
                bNames[s['shape']] = s['name']

        xMin = x1 - padding
        xMax = x2 + padding
        yMin = y1 - padding
        yMax = y2 + padding
        zMin = z1 - padding
        zMax = z2 + padding

        self._data = {
            'scale': 1.0,
            'vertices': [
                [xMin, yMin, zMin],
                [xMax, yMin, zMin],
                [xMax, yMax, zMin],
                [xMin, yMax, zMin],
                [xMin, yMin, zMax],
                [xMax, yMin, zMax],
                [xMax, yMax, zMax],
                [xMin, yMax, zMax]
            ],
            'blocks': [
                (
                    'hex', [0, 1, 2, 3, 4, 5, 6, 7],
                    [cx, cy, cz], ' ',
                    'simpleGrading', gradingRatio
                )
            ],
            'boundary': [
                (bNames[Shape.X_MIN.value], {
                    'type': 'patch',
                    'faces': [
                        [0, 3, 7, 4]
                    ]
                }),
                (bNames[Shape.X_MAX.value], {
                    'type': 'patch',
                    'faces': [
                        [1, 2, 6, 5]
                    ]
                }),
                (bNames[Shape.Y_MIN.value], {
                    'type': 'patch',
                    'faces': [
                        [0, 1, 5, 4]
                    ]
                }),
                (bNames[Shape.Y_MAX.value], {
                    'type': 'patch',
                    'faces': [
                        [3, 7, 6, 2]
                    ]
                }),
                (bNames[Shape.Z_MIN.value], {
                    'type': 'patch',
                    'faces': [
                        [0, 1, 2, 3]
                    ]
                }),
                (bNames[Shape.Z_MAX.value], {
                    'type': 'patch',
                    'faces': [
                        [4, 5, 6, 7]
                    ]
                })
            ]
        }

        return self
