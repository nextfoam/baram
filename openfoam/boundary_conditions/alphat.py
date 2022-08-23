#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.boundary_db import BoundaryDB, BoundaryType, WallVelocityCondition, InterfaceMode
from coredb.models_db import ModelsDB
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Alphat(BoundaryCondition):
    DIMENSIONS = '[1 -1 -1  0 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.boundaryLocation(rname), 'alphat')

        self._rname = rname
        self._db = coredb.CoreDB()
        # ToDo: Set initialValue
        self._initialValue = 0

        self._data = None

    def build(self):
        self._data = None

        if ModelsDB.isEnergyModelOn():
            self._data = {
                'dimensions': self.DIMENSIONS,
                'internalField': ('uniform', self._initialValue),
                'boundaryField': self._constructBoundaryField()
            }

        return self

    def _constructBoundaryField(self):
        field = {}

        boundaries = self._db.getBoundaryConditions(self._rname)
        for bcid, name, type_ in boundaries:
            xpath = BoundaryDB.getXPath(bcid)

            field[name] = {
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletAlphat(xpath)),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.SUBSONIC_INFLOW.value:     (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructCalculated(self._initialValue)),
                BoundaryType.WALL.value:                (lambda: self._constructWallAlphat(xpath)),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructCompressibleAlphatJayatillekeWallFunction()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceAlphat(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_)()

        return field

    def _constructCompressibleAlphatWallFunction(self):
        return {
            'type': 'compressible::alphatWallFunction',
            'Prt': self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/wallPrandtlNumber'),
            'value': ('uniform', self._initialValue)
        }

    def _constructCompressibleAlphatJayatillekeWallFunction(self):
        return {
            'type': 'alphatJayatillekeWallFunction',
            'Prt': self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/wallPrandtlNumber'),
            'value': ('uniform', self._initialValue)
        }

    def _constructPressureOutletAlphat(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructCalculated(self._initialValue)
        else:
            return self._constructZeroGradient()

    def _constructWallAlphat(self, xpath):
        spec = self._db.getValue(xpath + '/wall/velocity/type')
        if spec == WallVelocityCondition.ATMOSPHERIC_WALL.value:
            return self._constructCalculated(self._initialValue)
        else:
            return self._constructCompressibleAlphatWallFunction()

    def _constructInterfaceAlphat(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructCompressibleAlphatJayatillekeWallFunction()
        else:
            return self._constructCyclicAMI()
