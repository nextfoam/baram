#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import ZoneType, CellZoneDB
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.openfoam.file_system import FileSystem


class MRFProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'MRFProperties')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        db = coredb.CoreDB()

        mrfCellZoneConditions = db.getCellZonesByType(self._rname, ZoneType.MRF.value)
        if mrfCellZoneConditions:
            self._data = {}

            for czid in mrfCellZoneConditions:
                xpath = CellZoneDB.getXPath(czid)
                name = db.getValue(xpath + '/name')
                boundaries = db.getValue(xpath + '/mrf/staticBoundaries').split()

                self._data[f'MRFCellZone_{name}'] = {
                    'cellZone': name,
                    'active': 'yes',
                    'nonRotatingPatches': [BoundaryDB.getBoundaryName(b) for b in boundaries],
                    'origin': db.getVector(xpath + '/mrf/rotationAxisOrigin'),
                    'axis': db.getVector(xpath + '/mrf/rotationAxisDirection'),
                    'omega': float(db.getValue(xpath + '/mrf/rotatingSpeed')) * 2 * 3.141592 / 60
                }

        return self
