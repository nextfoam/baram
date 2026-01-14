#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Specie(BoundaryCondition):
    DIMENSIONS = '[0 0 0 0 0 0 0]'

    def __init__(self, region, time, processorNo, mid, name):
        super().__init__(region, time, processorNo, name)

        self._region = region
        self._mid = mid
        self._initialValue = region.initialSpecie(mid)

    def build0(self):
        self._data = None

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

            value = self._db.getValue(
                f'{xpath}/species/mixture[mid="{self._region.mid}"]/specie[mid="{self._mid}"]/value')

            field[name] = {
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructFixedValue(value)),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructFixedValue(value)),
                BoundaryType.FLOW_RATE_OUTLET.value:    (lambda: self._constructZeroGradient()),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructFixedValue(value)),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletSpecie(xpath, value)),
                BoundaryType.INTAKE_FAN.value:          (lambda: self._constructFixedValue(value)),
                BoundaryType.EXHAUST_FAN.value:         (lambda: self._constructZeroGradient()),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructFixedValue(value)),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructFixedValue(value)),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructZeroGradient()),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreeStream(value)),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructInletOutlet(value)),
                BoundaryType.SUBSONIC_INLET.value:      (lambda: self._constructFixedValue(value)),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructZeroGradient()),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructFixedValue(value)),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                BoundaryType.WALL.value:                (lambda: self._constructZeroGradient()),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructZeroGradient()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceSpecie(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_)()

        return field

    def _constructPressureOutletSpecie(self, xpath, value):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructInletOutlet(value)
        else:
            return self._constructZeroGradient()

    def _constructInterfaceSpecie(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructZeroGradient()
        else:
            return self._constructCyclicAMI()
