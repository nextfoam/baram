#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, ContactAngleModel, InterfaceMode
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Alpha(BoundaryCondition):
    DIMENSIONS = '[0 0 0 0 0 0 0]'

    def __init__(self, region, time, processorNo, mid):
        super().__init__(region, time, processorNo, 'alpha.' + MaterialDB.getName(mid))

        self._mid = mid

        xpath = RegionDB.getXPath(region.rname)
        self._initialValue = self._db.getValue(
            f'{xpath}/initialization/initialValues/volumeFractions/volumeFraction[material="{mid}"]/fraction')

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
            volumeFraction = self._db.getValue(f'{xpath}/volumeFractions/volumeFraction[material="{self._mid}"]/fraction')

            field[name] = {
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructFixedValue(volumeFraction)),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructFixedValue(volumeFraction)),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructFixedValue(volumeFraction)),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletAlpha(xpath, volumeFraction)),
                BoundaryType.ABL_INLET.value:           (lambda: None),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructVariableHeightFlowRate()),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructVariableHeightFlowRate()),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructZeroGradient()),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: None),
                BoundaryType.SUBSONIC_INFLOW.value:     (lambda: None),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: None),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: None),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: None),
                BoundaryType.WALL.value:                (lambda: self._constructWallAlpha(xpath)),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructZeroGradient()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceAlpha(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructZeroGradient()),
                BoundaryType.FAN.value:                 (lambda: self._constructZeroGradient()),
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
            'upperBound': 0.9,
            'value': self._initialValueByTime()
        }

    def _constructWallAlpha(self, xpath):
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
