#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import ZoneType, CellZoneDB
from baramFlow.openfoam.file_system import FileSystem


class DynamicMeshDict(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'dynamicMeshDict')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        db = coredb.CoreDB()

        zones = db.getCellZonesByType(self._rname, ZoneType.SLIDING_MESH.value)
        if zones:
            self._data = {
                'dynamicFvMesh': 'dynamicMotionSolverListFvMesh',
                'motionSolverLibs': ['"libfvMotionSolvers.so"'],
                'motionSolver': 'fvMotionSolvers',
                'solvers': {}
            }

            for czid in zones:
                xpath = CellZoneDB.getXPath(czid)
                name = db.retrieveValue(xpath + '/name')

                self._data['solvers'][f'sliding_{name}'] = {
                    'solver': 'solidBody',
                    'solidBodyMotionFunction': 'rotatingMotion',
                    'cellZone': name,
                    'rotatingMotionCoeffs': {
                        'origin': db.getVector(xpath + '/slidingMesh/rotationAxisOrigin'),
                        'axis': db.getVector(xpath + '/slidingMesh/rotationAxisDirection'),
                        'omega': float(db.retrieveValue(xpath + '/slidingMesh/rotatingSpeed')) * 2 * 3.141592 / 60
                    }
                }

        return self
