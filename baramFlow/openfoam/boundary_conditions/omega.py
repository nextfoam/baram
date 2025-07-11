#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, KOmegaSpecification, InterfaceMode, ShearCondition
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Omega(BoundaryCondition):
    DIMENSIONS = '[0 0 -1 0 0 0 0]'

    def __init__(self, region, time, processorNo):
        super().__init__(region, time, processorNo, 'omega')

        self._initialValue = region.initialOmega

    def build0(self):
        self._data = None

        if TurbulenceModelsDB.getRASModel() == TurbulenceModel.K_OMEGA and self._region.isFluid():
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
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletOmega(xpath)),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructAtmBoundaryLayerInletOmega()),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreeStreamOmega(xpath)),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_INLET.value:      (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructZeroGradient()),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructInletOutletByModel(xpath)),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                BoundaryType.WALL.value:                (lambda: self._constructWallOmega(xpath)),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructNEXTOmegaBlendedWallFunction()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceOmega(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_)()

        return field

    def _constructInletOutletByModel(self, xpath):
        spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
        if spec == KOmegaSpecification.K_AND_OMEGA.value:
            return self._constructInletOutlet(
                self._db.getValue(xpath + '/turbulence/k-omega/specificDissipationRate'))
        elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            return self._constructViscosityRatioInletOutletTDR(
                self._db.getValue(xpath + '/turbulence/k-omega/turbulentViscosityRatio'))

    def _constructAtmBoundaryLayerInletOmega(self):
        return {
            'type': 'atmBoundaryLayerInletOmega',
            'flowDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/flowDirection'),
            'zDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/groundNormalDirection'),
            'Uref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceFlowSpeed'),
            'Zref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceHeight'),
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate')
        }

    def _constructNEXTOmegaBlendedWallFunction(self):
        return {
            'type': 'omegaBlendedWallFunction',
            'blending': 'tanh',
            'value': self._initialValueByTime()
        }

    def _constructAtmOmegaWallFunction(self):
        return {
            'type': 'atmOmegaWallFunction',
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate'),
            'value': self._initialValueByTime()
        }

    def _constructPressureOutletOmega(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructInletOutletByModel(xpath)
        else:
            return self._constructZeroGradient()

    def _constructFreeStreamOmega(self, xpath):
        spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
        if spec == KOmegaSpecification.K_AND_OMEGA.value:
            return self._constructFreeStream(
                float(self._db.getValue(xpath + '/turbulence/k-omega/specificDissipationRate')))
        elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            return self._constructViscosityRatioInletOutletTDR(
                self._db.getValue(xpath + '/turbulence/k-omega/turbulentViscosityRatio'))

    def _constructWallOmega(self, xpath):
        if self._isAtmosphericWall(xpath):
            return self._constructAtmOmegaWallFunction()
        elif (self._db.getValue(xpath + '/wall/velocity/shearCondition') == ShearCondition.NO_SLIP.value
              and float(self._db.getValue(xpath + '/wall/velocity/wallRoughness/height')) > 0):
            return self._constructOmegaWallFunction()
        else:
            return self._constructNEXTOmegaBlendedWallFunction()

    def _constructInterfaceOmega(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructNEXTOmegaBlendedWallFunction()
        else:
            return self._constructCyclicAMI()

    def _constructOmegaWallFunction(self):
        return {
            'type': 'omegaWallFunction',
            'blending': 'tanh',
            'value': self._initialValueByTime()
        }
