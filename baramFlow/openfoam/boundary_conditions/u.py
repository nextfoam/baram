#!/usr/bin/env python
# -*- coding: utf-8 -*-

from math import sqrt

from baramFlow.coredb.project import Project
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, VelocitySpecification, VelocityProfile
from baramFlow.coredb.boundary_db import FlowRateInletSpecification, InterfaceMode
from baramFlow.coredb.boundary_db import WallMotion, ShearCondition, MovingWallMotion
from baramFlow.coredb.material_db import MaterialDB, UNIVERSAL_GAS_CONSTANT
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition
from libbaram.openfoam.dictionary.dictionary_file import DataClass


class U(BoundaryCondition):
    DIMENSIONS = '[0 1 -1 0 0 0 0]'

    def __init__(self, region, time, processorNo):
        super().__init__(region, time, processorNo, 'U', DataClass.CLASS_VOL_VECTOR_FIELD)

        self._initialValue = self._region.initialVelocity

    def build0(self):
        self._data = None

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
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructVelocityInletU(xpath, name)),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructFlowRateInletVelocity(xpath + '/flowRateInlet')),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructPressureInletOutletVelocity()),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletU(xpath)),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructAtmBoundaryLayerInletVelocity()),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructVariableHeightFlowRateInletVelocity(self._db.getValue(xpath + '/openChannelInlet/volumeFlowRate'))),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructOutletPhaseMeanVelocity(self._db.getValue(xpath + '/openChannelOutlet/meanVelocity'))),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreestreamVelocity(xpath + '/freeStream')),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructFarfieldRiemannU(xpath)),
                BoundaryType.SUBSONIC_INLET.value:      (lambda: self._constructSubsonicInlet(xpath + '/subsonicInlet')),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructSubsonicOutflow(xpath + '/subsonicOutflow')),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructFixedValue(self._db.getVector(xpath + '/supersonicInflow/velocity'))),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                BoundaryType.WALL.value:                (lambda: self._constructWallU(xpath)),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructNoSlip()),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceU(xpath)),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_)()

        return field

    def _constructFlowRateInletVelocity(self, xpath):
        spec = self._db.getValue(xpath + '/flowRate/specification')
        if spec == FlowRateInletSpecification.VOLUME_FLOW_RATE.value:
            return {
                'type': 'flowRateInletVelocity',
                'volumetricFlowRate': self._db.getValue(xpath + '/flowRate/volumeFlowRate')
            }
        elif spec == FlowRateInletSpecification.MASS_FLOW_RATE.value:
            return {
                'type': 'flowRateInletVelocity',
                'massFlowRate': self._db.getValue(xpath + '/flowRate/massFlowRate'),
                'rhoInlet': self._region.density
            }

    def _constructPressureInletOutletVelocity(self):
        return {
            'type': 'pressureInletOutletVelocity',
            'value': self._initialValueByTime()
        }

    def _constructPressureOutletU(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/nonReflective') == 'true':
            t = 300
            if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
                t = float(self._db.getValue(xpath + '/pressureOutlet/backflowTotalTemperature'))
            return self._constructWaveTransmissive(xpath, t)
        else:
            return self._constructPressureInletOutletVelocity()

    def _constructAtmBoundaryLayerInletVelocity(self):
        return {
            'type': 'atmBoundaryLayerInletVelocity',
            'flowDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/flowDirection'),
            'zDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/groundNormalDirection'),
            'Uref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceFlowSpeed'),
            'Zref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceHeight'),
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate')
        }

    def _constructVariableHeightFlowRateInletVelocity(self, flowRate):
        return {
            'type': 'variableHeightFlowRateInletVelocity',
            'alpha': 'alpha.' + MaterialDB.getName(self._region.secondaryMaterials[0]),
            'flowRate': flowRate,
            'value': self._initialValueByTime()
        }

    def _constructOutletPhaseMeanVelocity(self, Umean):
        return {
            'type': 'outletPhaseMeanVelocity',
            'alpha': 'alpha.' + MaterialDB.getName(self._region.secondaryMaterials[0]),
            'Umean': Umean
        }

    def _constructFreestreamVelocity(self, xpath):
        dx, dy, dz = self._db.getFlowDirection(xpath + '/flowDirection')
        dMag = sqrt(dx ** 2 + dy ** 2 + dz ** 2)
        speed = float(self._db.getValue(xpath + '/speed'))
        am = speed / dMag

        return {
            'type': 'freestreamVelocity',
            'freestreamValue': ('uniform', [am * dx, am * dy, am * dz])
        }

    def _constructNoSlip(self):
        # Can set to 'slip' but set to 'fixedValue' for paraview
        return self._constructFixedValue('(0 0 0)')

    def _constructMovingWallVelocity(self):
        return {
            'type': 'movingWallVelocity',
            'value': 'uniform (0 0 0)'
        }

    def _constructRotatingWallVelocity(self, xpath):
        return {
            'type': 'rotatingWallVelocity',
            'origin': self._db.getVector(xpath + '/rotationAxisOrigin'),
            'axis': self._db.getVector(xpath + '/rotationAxisDirection'),
            'omega': float(self._db.getValue(xpath + '/speed')) * 2 * 3.141592 / 60,
        }

    def _constructVelocityInletU(self, xpath, name):
        spec = self._db.getValue(xpath + '/velocityInlet/velocity/specification')
        if spec == VelocitySpecification.COMPONENT.value:
            profile = self._db.getValue(xpath + '/velocityInlet/velocity/component/profile')
            if profile == VelocityProfile.CONSTANT.value:
                return self._constructFixedValue(
                    self._db.getVector(xpath + '/velocityInlet/velocity/component/constant'))
            elif profile == VelocityProfile.SPATIAL_DISTRIBUTION.value:
                return self._constructTimeVaryingMappedFixedValue(
                    self._region.rname, name, 'U',
                    Project.instance().fileDB().getFileContents(
                        self._db.getValue(xpath + '/velocityInlet/velocity/component/spatialDistribution')))
            elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION.value:
                return self._constructUniformFixedValue(
                    xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear',
                    self.TableType.TEMPORAL_VECTOR_LIST)
        elif spec == VelocitySpecification.MAGNITUDE.value:
            profile = self._db.getValue(xpath + '/velocityInlet/velocity/magnitudeNormal/profile')
            if profile == VelocityProfile.CONSTANT.value:
                return self._constructSurfaceNormalFixedValue(
                    self._db.getValue(xpath + '/velocityInlet/velocity/magnitudeNormal/constant'))
            elif profile == VelocityProfile.SPATIAL_DISTRIBUTION.value:
                return self._constructTimeVaryingMappedFixedValue(
                    self._region.rname, name, 'U',
                    Project.instance().fileDB().getFileContents(
                        self._db.getValue(xpath + '/velocityInlet/velocity/magnitudeNormal/spatialDistribution')))
            elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION.value:
                return self._constructUniformNormalFixedValue(
                    xpath + '/velocityInlet/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear',
                    self.TableType.TEMPORAL_SCALAR_LIST)

    def _constructFarfieldRiemannU(self, xpath):
        gamma = 1.4
        mw = self._db.getMolecularWeight(MaterialDB.getMaterialComposition(xpath + '/species', self._region.mid))
        a = sqrt(gamma * (UNIVERSAL_GAS_CONSTANT / mw)
                 * float(self._db.getValue(xpath + '/farFieldRiemann/staticTemperature')))
        dx, dy, dz = self._db.getFlowDirection(xpath + '/farFieldRiemann/flowDirection')
        dMag = sqrt(dx ** 2 + dy ** 2 + dz ** 2)
        mInf = float(self._db.getValue(xpath + '/farFieldRiemann/machNumber'))
        am = a * mInf / dMag

        return self._constructFarfieldRiemann(xpath + '/farFieldRiemann', [am * dx, am * dy, am * dz])

    def _constructWallU(self, xpath):
        wallMotion = WallMotion(self._db.getValue(xpath + '/wall/velocity/wallMotion/type'))
        if wallMotion == WallMotion.STATIONARY_WALL:
            if self._db.getBool(xpath + '/wall/velocity/wallMotion/stationaryWall/atmosphericWall'):
                return self._constructNoSlip()
            elif self._db.getValue(xpath + '/wall/velocity/shearCondition') == ShearCondition.NO_SLIP.value:
                return self._constructNoSlip()
            else:
                return self._construcSlip()
        else:
            movingMotion = MovingWallMotion(self._db.getValue(xpath + '/wall/velocity/wallMotion/movingWall/motion'))
            if movingMotion == MovingWallMotion.TRANSLATIONAL_MOTION:
                return self._constructFixedValue(
                    self._db.getVector(xpath + '/wall/velocity/translationalMovingWall/velocity'))
            elif movingMotion == MovingWallMotion.ROTATIONAL_MOTION:
                return self._constructRotatingWallVelocity(xpath + '/wall/velocity/rotationalMovingWall')
            elif movingMotion == MovingWallMotion.MESH_MOTION:
                return self._constructMovingWallVelocity()

    def _constructInterfaceU(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructNoSlip()
        else:
            return self._constructCyclicAMI()
