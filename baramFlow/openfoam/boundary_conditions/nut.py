#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode, WallMotion, ShearCondition
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, KEpsilonModel, NearWallTreatment, TurbulenceModelsDB
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Nut(BoundaryCondition):
    DIMENSIONS = '[0 2 -1 0 0 0 0]'

    def __init__(self, region, time, processorNo):
        super().__init__(region, time, processorNo, 'nut')

        self._initialValue = region.initialNut
        self._model = TurbulenceModelsDB.getModel()

    def build0(self):
        if self._model == TurbulenceModel.LAMINAR:
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
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletNut(xpath)),
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
                BoundaryType.WALL.value:                (lambda: self._constructWallNut(xpath)),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructWallFunctionByModel()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceNut(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_)()

        return field

    def _constructWallFunctionByModel(self):
        if self._model == TurbulenceModel.K_EPSILON:
            # Wall type should be "nutSpaldingWallFunction" for "realizableKEtwoLayer" model
            subModel = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/model')
            if subModel == KEpsilonModel.REALIZABLE.value:
                treatment = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/realizable/nearWallTreatment')
                if treatment == NearWallTreatment.ENHANCED_WALL_TREATMENT.value:
                    return self._constructNEXTNutSpaldingWallFunction()

            return self._constructNEXTNutkWallFunction()
        else:
            return self._constructNEXTNutSpaldingWallFunction()

    def _constructNEXTNutkWallFunction(self):
        return {
            'type': 'nutkWallFunction',
            'value': self._initialValueByTime()
        }

    def _constructNEXTNutSpaldingWallFunction(self):
        return {
            'type': 'nutSpaldingWallFunction',
            'value': self._initialValueByTime()
        }

    def _constructRoughWallFunctionByModel(self, xpath):
        if self._model == TurbulenceModel.K_EPSILON:
            # Wall type should be "nutUSpaldingWallFunction" for "realizableKEtwoLayer" model
            subModel = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/model')
            if subModel == KEpsilonModel.REALIZABLE.value:
                treatment = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/realizable/nearWallTreatment')
                if treatment == NearWallTreatment.ENHANCED_WALL_TREATMENT.value:
                    return self._constructNutURoughWallFunction(xpath)

            return self._constructNutkRoughWallFunctionn(xpath)
        else:
            return self._constructNutURoughWallFunction(xpath)

    def _constructNutkRoughWallFunctionn(self, xpath):
        return {
            'type': 'nutkRoughWallFunction',
            'Ks': ('uniform', self._db.getValue(xpath + '/wall/velocity/wallRoughness/height')),
            'Cs': ('uniform', self._db.getValue(xpath + '/wall/velocity/wallRoughness/constant')),
            'value': self._initialValueByTime()
        }

    def _constructNutURoughWallFunction(self, xpath):
        return {
            'type': 'nutURoughWallFunction',
            'roughnessHeight': self._db.getValue(xpath + '/wall/velocity/wallRoughness/height'),
            'roughnessConstant': self._db.getValue(xpath + '/wall/velocity/wallRoughness/constant'),
            'roughnessFactor': 1,
            'value': self._initialValueByTime()
        }

    def _constructAtmNutkWallFunction(self):
        return {
            'type': 'atmNutkWallFunction',
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'value': self._initialValueByTime()
        }

    def _constructPressureOutletNut(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructCalculated()
        else:
            return self._constructZeroGradient()

    def _constructWallNut(self, xpath):
        isRoughWall = float(self._db.getValue(xpath + '/wall/velocity/wallRoughness/height')) > 0
        wallMotion = WallMotion(self._db.getValue(xpath + '/wall/velocity/wallMotion/type'))
        if wallMotion == WallMotion.STATIONARY_WALL:
            if self._db.getBool(xpath + '/wall/velocity/wallMotion/stationaryWall/atmosphericWall'):
                return self._constructAtmNutkWallFunction()

            if self._db.getValue(xpath + '/wall/velocity/shearCondition') == ShearCondition.SLIP.value:
                isRoughWall = False

        if isRoughWall:
            return self._constructRoughWallFunctionByModel(xpath)
        else:
            return self._constructWallFunctionByModel()

    def _constructInterfaceNut(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructWallFunctionByModel()
        else:
            return self._constructCyclicAMI()
