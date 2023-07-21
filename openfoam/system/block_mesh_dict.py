#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import app
from openfoam.dictionary_file import DictionaryFile


class BlockMeshDict(DictionaryFile):
    def __init__(self, rname: str = ''):
        super().__init__(self.systemLocation(rname), 'blockMeshDict')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        gradingRatio = [1, 1, 1]

        bounds = app.window.geometryManager().getBounds()
        xMin = bounds.xMin
        xMax = bounds.xMax
        yMin = bounds.yMin
        yMax = bounds.yMax
        zMin = bounds.zMin
        zMax = bounds.zMax

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
                [  # Cell Count for each direction
                    app.db.getValue('baseGrid/numCellsX'),
                    app.db.getValue('baseGrid/numCellsY'),
                    app.db.getValue('baseGrid/numCellsZ')
                ],
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
