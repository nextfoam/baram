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
    p1: str
    p2: str

    model: ExtrudeModel

    thickness: str = None

    point: list = None
    axis: list = None
    angle: str = None


class ExtrudeMeshDict(DictionaryFile):
    def __init__(self, fileSystem):
        super().__init__(fileSystem.caseRoot(), self.systemLocation(), 'extrudeMeshDict')

    def build(self, options):
        self._data = {
            'constructFrom': 'patch',
            'sourceCase': '"."',
            # 'sourceCase': str(app.fileSystem.caseRoot()),
            'sourcePatches': [options.p1],
            'exposedPatchName': options.p2,
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
