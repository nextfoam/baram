#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, KEpsilonSpecification, InterfaceMode
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, KEpsilonModel, NearWallTreatment, TurbulenceModelsDB
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Epsilon(BoundaryCondition):
    DIMENSIONS = '[0 2 -3 0 0 0 0]'

    def __init__(self, region, time, processorNo):
        super().__init__(region, time, processorNo, 'epsilon')

        self._initialValue = region.initialEpsilon

    def build0(self):
        self._data = None

        if TurbulenceModelsDB.getModel() == TurbulenceModel.K_EPSILON and self._region.isFluid():
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
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletEpsilon(xpath)),
                BoundaryType.INTAKE_FAN.value:          (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.EXHAUST_FAN.value:         (lambda: self._constructZeroGradient()),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructAtmBoundaryLayerInletEpsilon()),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreeStreamEpsilon(xpath)),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_INLET.value:      (lambda: self._constructInletOutletByModel(xpath)),
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
                self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentDissipationRate'))
        elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            return self._constructViscosityRatioInletOutletTDR(
                self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'))

    def _constructAtmBoundaryLayerInletEpsilon(self):
        if self._db.getAttribute(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/pasquillStability', 'disabled') == 'true':
            return self._constructAtmBoundaryLayerInlet('atmBoundaryLayerInletEpsilon')
        else:
            return self._constructPasquillAtmBoundaryLayerInlet('pasquillAtmBoundaryLayerInletEpsilon')

    def _constructNEXTEpsilonWallFunction(self):
        data = {
            'type': 'epsilonWallFunction',
            'value': self._initialValueByTime()
        }

        # Wall type should be "epsilonBlendedWallFunction" for "realizableKEtwoLayer" model
        turbulenceModel = TurbulenceModelsDB.getModel()
        if turbulenceModel == TurbulenceModel.K_EPSILON:
            subModel = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/model')
            if subModel == KEpsilonModel.REALIZABLE.value:
                treatment = self._db.getValue(
                    TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/realizable/nearWallTreatment')
                if treatment == NearWallTreatment.ENHANCED_WALL_TREATMENT.value:
                    data['type'] = 'epsilonBlendedWallFunction'

        return data

    def _constructAtmEpsilonWallFunction(self):
        return {
            'type': 'atmEpsilonWallFunction',
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate'),
            'value': self._initialValueByTime()
        }

    def _constructWallEpsilon(self, xpath):
        if self._isAtmosphericWall(xpath):
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
            return self._constructFreeStream(
                float(self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentDissipationRate')))
        elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            return self._constructViscosityRatioInletOutletTDR(
                self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'))

    def _constructInterfaceEpsilon(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructNEXTEpsilonWallFunction()
        else:
            return self._constructCyclicAMI()
