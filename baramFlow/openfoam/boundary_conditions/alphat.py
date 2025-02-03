#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode, WallTemperature
from baramFlow.coredb.turbulence_model_db import TurbulenceModelsDB, TurbulenceModel
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Alphat(BoundaryCondition):
    DIMENSIONS = '[1 -1 -1  0 0 0 0]'

    def __init__(self, region, time, processorNo):
        super().__init__(region, time, processorNo, 'alphat')

        self._initialValue = region.initialAlphat

    def build0(self):
        if TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR:
            return None

        if self._region.isFluid():
            self._data = {
                'dimensions': self.DIMENSIONS,
                'internalField': ('uniform', self._initialValue),
                'boundaryField': self._constructBoundaryField()
            }

        return self

    def _constructBoundaryField(self):
        field = {}

        for bcid, name, type_ in self._region.boundaries:
            xpath = BoundaryDB.getXPath(bcid)

            field[name] = {
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructCalculated()),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructCalculated()),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructCalculated()),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletAlphat(xpath)),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructCalculated()),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructCalculated()),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructCalculated()),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructCalculated()),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructCalculated()),
                BoundaryType.SUBSONIC_INLET.value:      (lambda: self._constructCalculated()),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructCalculated()),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructCalculated()),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructCalculated()),
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
            'Prt': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/wallPrandtlNumber'),
            'value': self._initialValueByTime()
        }

    def _constructCompressibleAlphatJayatillekeWallFunction(self):
        return {
            'type': 'compressible::alphatJayatillekeWallFunction',
            'Prt': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/wallPrandtlNumber'),
            'value': self._initialValueByTime()
        }

    def _constructPressureOutletAlphat(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructCalculated()
        else:
            return self._constructZeroGradient()

    def _constructWallAlphat(self, xpath):
        if self._isAtmosphericWall(xpath):
            return self._constructCalculated()
        else:
            spec = self._db.getValue(xpath + '/wall/temperature/type')
            if spec == WallTemperature.ADIABATIC.value:
                return self._constructCompressibleAlphatWallFunction()
            else:
                return self._constructCompressibleAlphatJayatillekeWallFunction()

    def _constructInterfaceAlphat(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructCompressibleAlphatJayatillekeWallFunction()
        else:
            return self._constructCyclicAMI()
