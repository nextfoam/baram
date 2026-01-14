#!/usr/bin/env python
# -*- coding: utf-8 -*-

from itertools import combinations

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, ContactAngleModel, InterfaceMode
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition
from baramFlow.openfoam.solver import findSolver


class Alpha(BoundaryCondition):
    DIMENSIONS = '[0 0 0 0 0 0 0]'

    def __init__(self, region, time, processorNo, mid: str):
        super().__init__(region, time, processorNo, 'alpha.' + MaterialDB.getName(mid))

        self._mid = mid

        if mid != region.mid:  # This material is not primary material
            self._initialValue = self._getInitialFraction(mid)
        else:
            sumFractions = 0.0
            for s in region.secondaryMaterials:
                sumFractions += float(self._getInitialFraction(s))
            self._initialValue = 1.0 - sumFractions

    def build0(self):
        self._data = None

        if ModelsDB.isMultiphaseModelOn() and self._region.secondaryMaterials:
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

            if self._mid != self._region.mid:  # This material is not primary material
                volumeFraction = self._getBoundaryFraction(bcid, self._mid)
            else:
                sumFractions = 0.0
                for s in self._region.secondaryMaterials:
                    fraction = self._getBoundaryFraction(bcid, s)
                    sumFractions += float(fraction)
                volumeFraction = 1.0 - sumFractions

            field[name] = {
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructFixedValue(volumeFraction)),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructFixedValue(volumeFraction)),
                BoundaryType.FLOW_RATE_OUTLET.value:    (lambda: self._constructZeroGradient()),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructFixedValue(volumeFraction)),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletAlpha(xpath, volumeFraction)),
                BoundaryType.INTAKE_FAN.value:          (lambda: self._constructFixedValue(volumeFraction)),
                BoundaryType.EXHAUST_FAN.value:         (lambda: self._constructZeroGradient()),
                BoundaryType.ABL_INLET.value:           (lambda: None),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructVariableHeightFlowRate()),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructVariableHeightFlowRate()),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructZeroGradient()),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: None),
                BoundaryType.SUBSONIC_INLET.value:      (lambda: None),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: None),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: None),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: None),
                BoundaryType.WALL.value:                (lambda: self._constructWallAlpha(xpath)),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructZeroGradient()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceAlpha(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_)()

        return field

    def _constructPressureOutletAlpha(self, xpath, inletValue):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructInletOutlet(inletValue)
        else:
            return self._constructZeroGradient()

    def _constructVariableHeightFlowRate(self):
        return {
            'type': 'variableHeightFlowRate',
            'lowerBound': 0.0,
            'upperBound': 1.0,
            'value': self._initialValueByTime()
        }

    def _constructWallAlpha(self, xpath):
        # "multiphaseInterFoam" has its own boundary type of "alphaContactAngle"
        if findSolver() == 'multiphaseInterFoam':
            return self._constructWallAlphaForMultiphaseInterFoam(xpath)

        contactAngleModel = self._db.getValue(xpath + '/wall/wallAdhesions/model')
        if contactAngleModel == ContactAngleModel.DISABLE.value:
            return self._constructZeroGradient()

        caXpath = f'{xpath}/wall/wallAdhesions/wallAdhesion[mid="{self._mid}"][mid="{self._region.mid}"]'
        if contactAngleModel == ContactAngleModel.CONSTANT.value:
            return {
                'type': 'constantAlphaContactAngle',
                'theta0': self._db.getValue(caXpath + '/contactAngle'),
                'limit': self._db.getValue(xpath + '/wall/wallAdhesions/limit'),
                'value': self._initialValueByTime()
            }
        elif contactAngleModel == ContactAngleModel.DYNAMIC.value:
            return {
                'type': 'dynamicAlphaContactAngle',
                'theta0': self._db.getValue(caXpath + '/contactAngle'),
                'uTheta': self._db.getValue(caXpath + '/characteristicVelocityScale'),
                'thetaA': self._db.getValue(caXpath + '/advancingContactAngle'),
                'thetaR': self._db.getValue(caXpath + '/recedingContactAngle'),
                'limit': self._db.getValue(xpath + '/wall/wallAdhesions/limit'),
                'value': self._initialValueByTime()
            }

    def _constructInterfaceAlpha(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return None
        else:
            return self._constructCyclicAMI()

    def _getInitialFraction(self, mid: str) -> str:
        xpath = RegionDB.getXPath(self._region.rname)
        fraction = self._db.getValue(
            f'{xpath}/initialization/initialValues/volumeFractions/volumeFraction[material="{mid}"]/fraction')

        return fraction

    def _getBoundaryFraction(self, bcid: int, mid: str) -> str:
        xpath = BoundaryDB.getXPath(bcid)
        fraction = self._db.getValue(f'{xpath}/volumeFractions/volumeFraction[material="{mid}"]/fraction')

        return fraction

    def _constructWallAlphaForMultiphaseInterFoam(self, xpath):
        if self._mid != self._region.mid:  # This material is not primary material
            return self._constructZeroGradient()

        # The code from here applies only to primary material

        contactAngleModel = ContactAngleModel(self._db.getValue(xpath + '/wall/wallAdhesions/model'))

        if contactAngleModel == ContactAngleModel.DISABLE:
            return self._constructZeroGradient()

        materials = [self._mid, *self._region.secondaryMaterials]
        valueList = []
        for mid1, mid2 in combinations(materials, 2):
            name1 = MaterialDB.getName(mid1)
            name2 = MaterialDB.getName(mid2)
            caXpath = f'{xpath}/wall/wallAdhesions/wallAdhesion[mid="{mid1}"][mid="{mid2}"]'

            theta0 = self._db.getValue(caXpath + '/contactAngle')

            if contactAngleModel == ContactAngleModel.DYNAMIC:
                uTheta = self._db.getValue(caXpath + '/characteristicVelocityScale')
                thetaA = self._db.getValue(caXpath + '/advancingContactAngle')
                thetaR = self._db.getValue(caXpath + '/recedingContactAngle')
            else:  # contactAngleModel == ContactAngleModel.CONSTANT:
                uTheta = 0
                thetaA = 0
                thetaR = 0

            valueList.extend([
                [name1, name2],
                theta0,
                uTheta,
                thetaA,
                thetaR
            ])
        return {
            'type': 'alphaContactAngle',
            'thetaProperties': valueList,
            'value': self._initialValueByTime()
        }
