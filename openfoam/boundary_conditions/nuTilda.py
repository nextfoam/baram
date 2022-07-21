#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.boundary_db import BoundaryDB, BoundaryType, SpalartAllmarasSpecification, InterfaceMode
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class NuTilda(BoundaryCondition):
    DIMENSIONS = '[0 2 -1 0 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.boundaryLocation(rname), 'nuTilda')

        self._rname = rname
        self._db = coredb.CoreDB()
        # ToDo: Set initialValue
        self._initialValue = 0

    def build(self):
        if self._data is not None:
            return self

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
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructFixedValueByModel(xpath)),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructFixedValueByModel(xpath)),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructFixedValueByModel(xpath)),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletNuTilda(xpath)),
                BoundaryType.ABL_INLET.value:           (lambda: None),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreestream(xpath + '/freeStream')),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_INFLOW.value:     (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructZeroGradient()),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                BoundaryType.WALL.value:                (lambda: self._constructZeroGradient()),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructZeroGradient()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceNuTilda(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_)()

        return field

    def _constructFixedValueByModel(self, xpath):
        spec = self._db.getValue(xpath + '/turbulence/spalartAllmaras/specification')
        if spec == SpalartAllmarasSpecification.MODIFIED_TURBULENT_VISCOSITY.value:
            return self._constructFixedValue(
                self._db.getValue(xpath + '/turbulence/spalartAllmaras/modifiedTurbulentViscosity'))
        elif spec == SpalartAllmarasSpecification.TURBULENT_VISCOSITY_RATIO.value:
            # ToDo: Setting according to boundary field spec
            return {
                'type': ''
            }

    def _constructInletOutletByModel(self, xpath):
        spec = self._db.getValue(xpath + '/turbulence/spalartAllmaras/specification')
        if spec == SpalartAllmarasSpecification.MODIFIED_TURBULENT_VISCOSITY.value:
            return self._constructInletOutlet(
                self._db.getValue(xpath + '/turbulence/spalartAllmaras/modifiedTurbulentViscosity'), self._initialValue)
        elif spec == SpalartAllmarasSpecification.TURBULENT_VISCOSITY_RATIO.value:
            # ToDo: Setting according to boundary field spec
            return {
                'type': ''
            }

    def _constructPressureOutletNuTilda(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructInletOutletByModel(xpath)
        else:
            return self._constructZeroGradient()

    def _constructInterfaceNuTilda(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructZeroGradient()
        else:
            return self._constructCyclicAMI()
