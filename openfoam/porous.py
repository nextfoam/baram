#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.setup.cell_zone_conditions.cell_zone_db import CellZoneDB, PorousZoneModel


class Porous:
    def __init__(self, czid):
        self._db = coredb.CoreDB()
        self._xpath = CellZoneDB.getXPath(czid)
        self._data = None

    def buildDict(self):
        if self._data is not None:
            return self

        model = self._db.getValue(self._xpath + '/porous/model')

        self._data = {
            'type': 'explicitPorositySource',
            'active': 'true',
            'explicitPorositySourceCoeffs': {
                'selectionMode': 'cellZone',
                'cellZone': self._db.getValue(self._xpath + '/name'),
                'type': model,
                'active': 'yes',
            }
        }

        if model == PorousZoneModel.DARCY_FORCHHEIMER.value:
            self._data['DarcyForchheimerCoeffs'] = self._constructDarcyForchheimerCoeffs()
        else:
            self._data['powerLawCoeffs'] = self._constructPowerLawCoeffs()

        return self._data

    def _constructDarcyForchheimerCoeffs(self):
        # ToDo : d, f, e1, e2
        return {
            'd': ('d [0 -2 0 0 0 0 0]', self._db.getVector(self._xpath)),
            'f': ('f [0 -1 0 0 0 0 0]', self._db.getVector(self._xpath)),
            'coordinateSystem': {
                'type': 'cartesian',
                'origin': '(0 0 0)',
                'coordinateRotation': {
                    'type': 'axesRotation',
                    'e1': self._db.getVector(self._xpath),
                    'e2': self._db.getVector(self._xpath)
                }
            }
        }

    def _constructPowerLawCoeffs(self):
        return {
            'C0': self._db.getValue(self._xpath + '/porous/powerLaw/c0'),
            'C1': self._db.getValue(self._xpath + '/porous/powerLaw/c1')
        }
