#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from coredb import coredb
from view.setup.cell_zone_conditions.cell_zone_db import ZoneType, CellZoneDB
from view.setup.boundary_conditions.boundary_db import BoundaryDB


class MRFProperties(object):
    def __init__(self, rname: str):
        self._rname = rname
        self._data = None

    def __str__(self):
        return self.asStr()

    def _build(self):
        if self._data is not None:
            return

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

    def asDict(self):
        self._build()
        return self._data

    def asStr(self):
        HEADER = {
            'version': '2.0',
            'format': 'ascii',
            'class': 'dictionary',
            'location': f'constant/{self._rname}',
            'object': 'MRFProperties'
        }
        self._build()
        return str(FoamFileGenerator(self._data, header=HEADER)) if self._data else ''
