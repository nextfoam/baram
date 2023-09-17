#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import app
from openfoam.dictionary_file import DictionaryFile


class BlockMeshDict(DictionaryFile):
    def __init__(self):
        super().__init__()
        self._setHeader(self.systemLocation(), 'blockMeshDict')

    def build(self):
        if self._data is not None:
            return self

        gradingRatio = [1, 1, 1]

        bounds = app.window.geometryManager.getBounds()
        cellCounts = app.db.getValues('baseGrid', ['numCellsX', 'numCellsY', 'numCellsZ'])
        padding = min([s / int(c) for s, c in zip(bounds.size(), cellCounts)]) / 100

        xMin = bounds.xMin - padding
        xMax = bounds.xMax + padding
        yMin = bounds.yMin - padding
        yMax = bounds.yMax + padding
        zMin = bounds.zMin - padding
        zMax = bounds.zMax + padding

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
                ('hex', [0, 1, 2, 3, 4, 5, 6, 7]),
                cellCounts,
                ('simpleGrading', gradingRatio)
            ],
            'boundary': [
                ('xMin', {
                    'type': 'patch',
                    'faces': [
                        [0, 3, 7, 4]
                    ]
                }),
                ('xMax', {
                    'type': 'patch',
                    'faces': [
                        [1, 2, 6, 5]
                    ]
                }),
                ('yMin', {
                    'type': 'patch',
                    'faces': [
                        [0, 1, 5, 4]
                    ]
                }),
                ('yMax', {
                    'type': 'patch',
                    'faces': [
                        [3, 7, 6, 2]
                    ]
                }),
                ('zMin', {
                    'type': 'patch',
                    'faces': [
                        [0, 1, 2, 3]
                    ]
                }),
                ('zMax', {
                    'type': 'patch',
                    'faces': [
                        [4, 5, 6, 7]
                    ]
                })
            ]
        }

        return self
