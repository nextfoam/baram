#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math

from coredb import coredb
from coredb.cell_zone_db import RegionDB
from coredb.material_db import MaterialDB, Phase
from coredb.boundary_db import BoundaryDB, BoundaryType, KEpsilonSpecification, WallVelocityCondition, WallVelocityCondition, InterfaceMode
from coredb.models_db import ModelsDB, TurbulenceModel
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Epsilon(BoundaryCondition):
    DIMENSIONS = '[0 2 -3 0 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.boundaryLocation(rname), 'epsilon')

        self._rname = rname
        self._db = coredb.CoreDB()

        p = float(self._db.getValue('.//initialization/initialValues/pressure'))\
            + float(self._db.getValue('.//operatingConditions/pressure'))  # Pressure
        t = float(self._db.getValue('.//initialization/initialValues/temperature'))  # Temperature
        v = float(self._db.getValue('.//initialization/initialValues/scaleOfVelocity'))  # Scale of Velocity
        i = float(self._db.getValue('.//initialization/initialValues/turbulentIntensity')) / 100.0  # Turbulent Intensity
        b = float(self._db.getValue('.//initialization/initialValues/turbulentViscosity'))  # Turbulent Viscosity

        mid = RegionDB.getMaterial(rname)
        assert MaterialDB.getPhase(mid) in [Phase.LIQUID, Phase.GAS]

        rho = MaterialDB.getDensity(mid, t, p)  # Density
        mu = MaterialDB.getViscosity(mid, t)  # Viscosity

        nu = mu / rho  # Kinetic Viscosity
        nut = b * nu

        k = 1.5 * math.sqrt(v*i)
        e = 0.09 * math.sqrt(k) / nut

        self._initialValue = e

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

        boundaries = self._db.getBoundaryConditions(self._rname)
        for bcid, name, type_ in boundaries:
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
                self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'))

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
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate')
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
            return self._constructFreestream(xpath + '/freeStream')
        elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            return self._constructNEXTViscosityRatioInletOutletTDR(
                self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'))

    def _constructInterfaceEpsilon(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructNEXTEpsilonWallFunction()
        else:
            return self._constructCyclicAMI()
