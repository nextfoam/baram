#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.boundary_db import BoundaryDB, BoundaryType, KEpsilonSpecification, KOmegaSpecification, InterfaceMode
from coredb.models_db import ModelsDB, TurbulenceModel
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class K(BoundaryCondition):
    DIMENSIONS = '[0 2 -2 0 0 0 0]'

    def __init__(self, rname: str):
        self._rname = rname
        super().__init__(self.boundaryLocation(rname), 'K')

        self._db = coredb.CoreDB()
        # ToDo: Set initialValue
        self._initialValue = 0
        self._specification = None
        self._model = ModelsDB.getTurbulenceModel()

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
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletK(xpath)),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructAtmBoundaryLayerInletK()),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreeStreamK(xpath)),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_INFLOW.value:     (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructZeroGradient()),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                BoundaryType.WALL.value:                (lambda: self._constructKqRWallFunction()),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructKqRWallFunction()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceK(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_)()

        return field

    def _constructInletOutletByModel(self, xpath):
        if self._model == TurbulenceModel.K_EPSILON:
            spec = self._db.getValue(xpath + '/turbulence/k-epsilon/specification')
            if spec == KEpsilonSpecification.K_AND_EPSILON.value:
                return self._constructInletOutlet(
                    self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentKineticEnergy'), self._initialValue)
            elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructNEXTTurbulentIntensityInletOutletTKE(
                    self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentIntensity'))
        elif self._model == TurbulenceModel.K_OMEGA:
            spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
            if spec == KOmegaSpecification.K_AND_OMEGA.value:
                return self._constructInletOutlet(
                    self._db.getValue(xpath + '/turbulence/k-omega/turbulentKineticEnergy'), self._initialValue)
            elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructNEXTTurbulentIntensityInletOutletTKE(
                    self._db.getValue(xpath + '/turbulence/k-omega/turbulentIntensity'))

    def _constructNEXTTurbulentIntensityInletOutletTKE(self, turbulentIntensity):
        return {
            'type': 'turbulentIntensityInletOutletTKE',
            'turbIntensity': turbulentIntensity
        }

    def _constructAtmBoundaryLayerInletK(self):
        return {
            'type': 'atmBoundaryLayerInletK',
            'flowDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/flowDirection'),
            'zDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/groundNormalDirection'),
            'Uref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceFlowSpeed'),
            'Zref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceHeight'),
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate')
        }

    def _constructKqRWallFunction(self):
        return {
            'type': 'kqRWallFunction',
            'value': ('uniform', self._initialValue)
        }

    def _constructPressureOutletK(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructInletOutletByModel(xpath)
        else:
            return self._constructZeroGradient()

    def _constructFreeStreamK(self, xpath):
        if self._model == TurbulenceModel.K_EPSILON:
            spec = self._db.getValue(xpath + '/turbulence/k-epsilon/specification')
            if spec == KEpsilonSpecification.K_AND_EPSILON.value:
                return self._constructFreestream(xpath + '/freeStream')
            elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructNEXTTurbulentIntensityInletOutletTKE(
                    self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentIntensity'))
        elif self._model == TurbulenceModel.K_OMEGA:
            spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
            if spec == KOmegaSpecification.K_AND_OMEGA.value:
                return self._constructFreestream(xpath + '/freeStream')
            elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructNEXTTurbulentIntensityInletOutletTKE(
                    self._db.getValue(xpath + '/turbulence/k-omega/turbulentIntensity'))

    def _constructInterfaceK(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructKqRWallFunction()
        else:
            return self._constructCyclicAMI()
