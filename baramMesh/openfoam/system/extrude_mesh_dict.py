#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile


class ExtrudeModel(Enum):
    PLANE = 'plane'
    WEDGE = 'wedge'


@dataclass
class ExtrudeOptions:
    model: ExtrudeModel

    thickness: str = None

    point: list = None
    axis: list = None
    angle: str = None


class ExtrudeMeshDict(DictionaryFile):
    def __init__(self, fileSystem):
        super().__init__(fileSystem.caseRoot(), self.systemLocation(), 'extrudeMeshDict')

    def build(self, p1, p2, options):
        self._data = {
            'constructFrom': 'patch',
            'sourceCase': '"."',
            # 'sourceCase': str(app.fileSystem.caseRoot()),
            'sourcePatches': [p1],
            'exposedPatchName': p2,
            'extrudeModel': options.model.value,
            'flipNormals': 'false',
            'mergeFaces': 'false',
        }

        if options.model == ExtrudeModel.PLANE:
            self._data['thickness'] = options.thickness
        elif options.model == ExtrudeModel.WEDGE:
            self._data['sectorCoeffs'] = {
                'point': options.point,
                'axis': options.axis,
                'angle': options.angle}

        return self
