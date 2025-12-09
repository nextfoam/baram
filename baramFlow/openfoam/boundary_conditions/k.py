#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.boundary_db import KEpsilonSpecification, KOmegaSpecification, InterfaceMode
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, SubgridKineticEnergySpecificationMethod
from baramFlow.coredb.turbulence_model_db import TurbulenceModelsDB
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class K(BoundaryCondition):
    DIMENSIONS = '[0 2 -2 0 0 0 0]'

    def __init__(self, region, time, processorNo):
        super().__init__(region, time, processorNo, 'k')

        self._initialValue = region.initialK
        self._model = TurbulenceModelsDB.getRASModel()

    def build0(self):
        self._data = None

        if not self._region.isFluid():
            return self

        if (self._model == TurbulenceModel.K_EPSILON or self._model == TurbulenceModel.K_OMEGA
                or TurbulenceModelsDB.isLESKEqnModel()):
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
                BoundaryType.FLOW_RATE_OUTLET.value:    (lambda: self._constructZeroGradient()),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletK(xpath)),
                BoundaryType.INTAKE_FAN.value:          (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.EXHAUST_FAN.value:         (lambda: self._constructZeroGradient()),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructAtmBoundaryLayerInletK()),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreeStreamK(xpath)),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_INLET.value:      (lambda: self._constructInletOutletByModel(xpath)),
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
                    self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentKineticEnergy'))
            elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructTurbulentIntensityInletOutletTKE(
                    float(self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentIntensity')) / 100.0)
        elif self._model == TurbulenceModel.K_OMEGA:
            spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
            if spec == KOmegaSpecification.K_AND_OMEGA.value:
                return self._constructInletOutlet(
                    self._db.getValue(xpath + '/turbulence/k-omega/turbulentKineticEnergy'))
            elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructTurbulentIntensityInletOutletTKE(
                    float(self._db.getValue(xpath + '/turbulence/k-omega/turbulentIntensity')) / 100.0)
        elif TurbulenceModelsDB.isLESKEqnModel():
            spec = self._db.getValue(xpath + '/turbulence/les/specification')
            if spec == SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_K.value:
                return self._constructInletOutlet(
                    self._db.getValue(xpath + '/turbulence/les/subgridKineticEnergy'))
            elif spec == SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_INTENSITY.value:
                return self._constructTurbulentIntensityInletOutletTKE(
                    float(self._db.getValue(xpath + '/turbulence/les/subgridTurbulentIntensity')) / 100.0)

    def _constructTurbulentIntensityInletOutletTKE(self, turbulentIntensity):
        return {
            'type': 'turbulentIntensityInletOutletTKE',
            'turbIntensity': ('uniform', turbulentIntensity),
            'value': self._initialValueByTime()
        }

    def _constructAtmBoundaryLayerInletK(self):
        if self._db.getAttribute(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/pasquillStability', 'disabled') == 'true':
            return self._constructAtmBoundaryLayerInlet('atmBoundaryLayerInletK')
        else:
            return self._constructPasquillAtmBoundaryLayerInlet('pasquillAtmBoundaryLayerInletK')
        # return {
        #     'type': 'atmBoundaryLayerInletK',
        #     'flowDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/flowDirection'),
        #     'zDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/groundNormalDirection'),
        #     'Uref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceFlowSpeed'),
        #     'Zref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceHeight'),
        #     'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
        #     'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate')
        # }

    def _constructKqRWallFunction(self):
        return {
            'type': 'kqRWallFunction',
            'value': self._initialValueByTime()
        }

    def _constructPressureOutletK(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructInletOutletByModel(xpath)
        else:
            return self._constructZeroGradient()

    def _constructFreeStreamK(self, xpath):
        k = None
        if self._model == TurbulenceModel.K_EPSILON:
            spec = self._db.getValue(xpath + '/turbulence/k-epsilon/specification')
            if spec == KEpsilonSpecification.K_AND_EPSILON.value:
                k = float(self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentKineticEnergy'))
            elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructTurbulentIntensityInletOutletTKE(
                    float(self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentIntensity')) / 100.0)
        elif self._model == TurbulenceModel.K_OMEGA:
            spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
            if spec == KOmegaSpecification.K_AND_OMEGA.value:
                k = float(self._db.getValue(xpath + '/turbulence/k-omega/turbulentKineticEnergy'))
            elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructTurbulentIntensityInletOutletTKE(
                    float(self._db.getValue(xpath + '/turbulence/k-omega/turbulentIntensity')) / 100.0)
        elif TurbulenceModelsDB.isLESKEqnModel():
            spec = self._db.getValue(xpath + '/turbulence/les/specification')
            if spec == SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_K.value:
                k = float(self._db.getValue(xpath + '/turbulence/les/subgridKineticEnergy'))
            elif spec == SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_INTENSITY.value:
                return self._constructTurbulentIntensityInletOutletTKE(
                    float(self._db.getValue(xpath + '/turbulence/les/subgridTurbulentIntensity')) / 100.0)

        return self._constructFreeStream(k)

    def _constructInterfaceK(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructKqRWallFunction()
        else:
            return self._constructCyclicAMI()
