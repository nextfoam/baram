#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

from coredb import coredb
from openfoam.dictionary_file import DictionaryFile
from coredb.boundary_db import BoundaryType
from .polymesh_loader import PolyMeshLoader


TYPE_MAP = {
    BoundaryType.VELOCITY_INLET.value: 'patch',
    BoundaryType.FLOW_RATE_INLET.value: 'patch',
    BoundaryType.PRESSURE_INLET.value: 'patch',
    BoundaryType.ABL_INLET.value: 'patch',
    BoundaryType.OPEN_CHANNEL_INLET.value: 'patch',
    BoundaryType.FREE_STREAM.value: 'patch',
    BoundaryType.FAR_FIELD_RIEMANN.value: 'patch',
    BoundaryType.SUBSONIC_INFLOW.value: 'patch',
    BoundaryType.SUPERSONIC_INFLOW.value: 'patch',
    BoundaryType.PRESSURE_OUTLET.value: 'patch',
    BoundaryType.OPEN_CHANNEL_OUTLET.value: 'patch',
    BoundaryType.OUTFLOW.value: 'patch',
    BoundaryType.SUBSONIC_OUTFLOW.value: 'patch',
    BoundaryType.SUPERSONIC_OUTFLOW.value: 'patch',
    BoundaryType.WALL.value: 'wall',
    BoundaryType.THERMO_COUPLED_WALL.value: 'mappedWall',
    BoundaryType.POROUS_JUMP.value: 'cycle',
    BoundaryType.FAN.value: 'cycle',
    BoundaryType.SYMMETRY.value: 'symetry',
    BoundaryType.INTERFACE.value: 'cyclicAMI',
    BoundaryType.EMPTY.value: 'enpty',
    BoundaryType.CYCLIC.value: 'cyclic',
    BoundaryType.WEDGE.value: 'wedge',
}

class Boundary(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(self.polyMeshLocation(rname), 'boundary')

        self._rname = rname
        self._boundaryDict = None

    def build(self, constantLoadingDir, casePath):
        if self._boundaryDict is not None:
            return self

        if not constantLoadingDir:
            return self

        db = coredb.CoreDB()

        fullPath = self.fullPath(casePath)
        shutil.copyfile(os.path.join(constantLoadingDir, self._rname, 'polyMesh', 'boundary'), fullPath)

        self._boundaryDict = PolyMeshLoader.loadBoundary(fullPath)
        boundaries = self._boundaryDict.content
        for bname in boundaries:
            boundaries[bname]['type'] = TYPE_MAP[
                db.getValue(
                    f'.//region[name="{self._rname}"]/boundaryConditions/boundaryCondition[name="{bname}"]/physicalType'
                )
            ]

        return self

    def write(self, caseRoot):
        self._boundaryDict.writeFile()

