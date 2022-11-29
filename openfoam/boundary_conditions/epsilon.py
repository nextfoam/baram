#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.boundary_db import BoundaryDB, BoundaryType, KEpsilonSpecification, WallVelocityCondition, InterfaceMode
from coredb.models_db import ModelsDB, TurbulenceModel
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Epsilon(BoundaryCondition):
    DIMENSIONS = '[0 2 -3 0 0 0 0]'

    def __init__(self, region):
        super().__init__(self.boundaryLocation(region.rname), 'epsilon')

        self._region = region
        self._db = coredb.CoreDB()

        self._initialValue = region.initialEpsilon

        self._data = None

    def build(self):
        self._data = None

        if ModelsDB.getTurbulenceModel() == TurbulenceModel.K_EPSILON:
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
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletEpsilon(xpath)),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructAtmBoundaryLayerInletEpsilon()),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreeStreamEpsilon(xpath)),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_INFLOW.value:     (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructZeroGradient()),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                BoundaryType.WALL.value:                (lambda: self._constructWallEpsilon(xpath)),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructNEXTEpsilonWallFunction()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceEpsilon(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_)()

        return field

    def _constructInletOutletByModel(self, xpath):
        spec = self._db.getValue(xpath + '/turbulence/k-epsilon/specification')
        if spec == KEpsilonSpecification.K_AND_EPSILON.value:
            return self._constructInletOutlet(
                self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentDissipationRate'), self._initialValue)
        elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            return self._constructNEXTViscosityRatioInletOutletTDR(
                self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'), self._initialValue)

    def _constructAtmBoundaryLayerInletEpsilon(self):
        return {
            'type': 'atmBoundaryLayerInletEpsilon',
            'flowDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/flowDirection'),
            'zDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/groundNormalDirection'),
            'Uref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceFlowSpeed'),
            'Zref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceHeight'),
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate')
        }

    def _constructNEXTEpsilonWallFunction(self):
        return {
            'type': 'epsilonWallFunction',
            'value': ('uniform', self._initialValue)
        }

    def _constructAtmEpsilonWallFunction(self):
        return {
            'type': 'atmEpsilonWallFunction',
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate'),
            'value': ('uniform', self._initialValue)
        }

    def _constructWallEpsilon(self, xpath):
        spec = self._db.getValue(xpath + '/wall/velocity/type')
        if spec == WallVelocityCondition.ATMOSPHERIC_WALL.value:
            return self._constructAtmEpsilonWallFunction()
        else:
            return self._constructNEXTEpsilonWallFunction()

    def _constructPressureOutletEpsilon(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructInletOutletByModel(xpath)
        else:
            return self._constructZeroGradient()

    def _constructFreeStreamEpsilon(self, xpath):
        spec = self._db.getValue(xpath + '/turbulence/k-epsilon/specification')
        if spec == KEpsilonSpecification.K_AND_EPSILON.value:
            epsilon = float(self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentDissipationRate'))
        elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            _, epsilon = self._calculateFreeStreamKE(xpath, self._region.rname)
        return self._constructFreestream(epsilon)

    def _constructInterfaceEpsilon(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructNEXTEpsilonWallFunction()
        else:
            return self._constructCyclicAMI()
