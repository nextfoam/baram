#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode
from baramFlow.coredb.turbulence_model_db import TurbulenceModelsDB, TurbulenceModel
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class ReThetat(BoundaryCondition):
    DIMENSIONS = '[0 0 0 0 0 0 0]'

    def __init__(self, region, time, processorNo):
        super().__init__(region, time, processorNo, 'ReThetat')

        self._initialValue = self._region.initialMomentumThicknessRe

    def build0(self):
        if TurbulenceModelsDB.getModel() != TurbulenceModel.TRANSITION_SST:
            return None

        self._data = {
            'dimensions': self.DIMENSIONS,
            'internalField': ('uniform', self._initialValue),
            'boundaryField': self._constructBoundaryField()
        }

        return self

    def _constructBoundaryField(self):
        field = {}

        for boundaryModel in BoundaryService.getBoundariesIn(self._region.rname):
            bcid = boundaryModel.boundary.bcid
            xpath = BoundaryDB.getXPath(bcid)

            value = self._db.getValue(f'{xpath}/turbulence/transitionSST/momentumThicknessRe')

            field[boundaryModel.boundary.name] = {
                BoundaryType.VELOCITY_INLET:        (lambda: self._constructFixedValue(value)),
                BoundaryType.FLOW_RATE_INLET:       (lambda: self._constructFixedValue(value)),
                BoundaryType.FLOW_RATE_OUTLET:      (lambda: self._constructZeroGradient()),
                BoundaryType.PRESSURE_INLET:        (lambda: self._constructFixedValue(value)),
                BoundaryType.PRESSURE_OUTLET:       (lambda: self._constructPressureOutletReThetat(xpath, value)),
                BoundaryType.INTAKE_FAN:            (lambda: self._constructFixedValue(value)),
                BoundaryType.EXHAUST_FAN:           (lambda: self._constructZeroGradient()),
                BoundaryType.ABL_INLET:             (lambda: self._constructFixedValue(value)),
                BoundaryType.OPEN_CHANNEL_INLET:    (lambda: self._constructFixedValue(value)),
                BoundaryType.OPEN_CHANNEL_OUTLET:   (lambda: self._constructZeroGradient()),
                BoundaryType.OUTFLOW:               (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM:           (lambda: self._constructInletOutlet(value)),
                BoundaryType.FAR_FIELD_RIEMANN:     (lambda: self._constructInletOutlet(value)),
                BoundaryType.SUBSONIC_INLET:        (lambda: self._constructFixedValue(value)),
                BoundaryType.SUBSONIC_OUTFLOW:      (lambda: self._constructZeroGradient()),
                BoundaryType.SUPERSONIC_INFLOW:     (lambda: self._constructFixedValue(value)),
                BoundaryType.SUPERSONIC_OUTFLOW:    (lambda: self._constructZeroGradient()),
                BoundaryType.WALL:                  (lambda: self._constructZeroGradient()),
                BoundaryType.THERMO_COUPLED_WALL:   (lambda: self._constructZeroGradient()),
                BoundaryType.SYMMETRY:              (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE:             (lambda: self._constructInterfaceReThetat(self._db.getValue(xpath + '/interface/mode'))),
                BoundaryType.POROUS_JUMP:           (lambda: self._constructCyclic()),
                BoundaryType.FAN:                   (lambda: self._constructCyclic()),
                BoundaryType.EMPTY:                 (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC:                (lambda: self._constructCyclic()),
                BoundaryType.CYCLIC_ACMI:           (lambda: self._constructCyclicACMI()),
                BoundaryType.WEDGE:                 (lambda: self._constructWedge())
            }.get(BoundaryDB.getBoundaryType(bcid), lambda: None)()

        return field

    def _constructPressureOutletReThetat(self, xpath: str, value: float):
        if self._db.getBool(xpath + '/pressureOutlet/calculatedBackflow'):
            return self._constructFixedValue(value)
        else:
            return self._constructZeroGradient()

    def _constructInterfaceReThetat(self, spec):
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructZeroGradient()
        else:
            return self._constructCyclicAMI()
