#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.setup.boundary_conditions.boundary_db import BoundaryListIndex, BoundaryDB, BoundaryType
from view.setup.boundary_conditions.boundary_db import VelocitySpecification, VelocityProfile
from view.setup.boundary_conditions.boundary_db import FlowRateInletSpecification, WallVelocityCondition, InterfaceMode
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition
from openfoam.dictionary_file import DataClass


class U(BoundaryCondition):
    DIMENSIONS = '[0 1 -1 0 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.boundaryLocation(rname), 'U', DataClass.CLASS_VOL_VECTOR_FIELD)

        self._rname = rname
        self._db = coredb.CoreDB()
        self._initialValue = self._db.getVector('.//initialization/initialValues/velocity')

    def build(self):
        if self._data is not None:
            return

        self._data = {
            'dimensions': self.DIMENSIONS,
            'internalField': ('uniform', self._initialValue),
            'boundaryField': self._constructBoundaryField()
        }

        return self

    def _constructBoundaryField(self):
        field = {}

        boundaries = self._db.getBoundaryConditions(self._rname)
        for b in boundaries:
            bcid = b[BoundaryListIndex.ID.value]
            name = b[BoundaryListIndex.NAME.value]
            type_ = b[BoundaryListIndex.TYPE.value]
            xpath = BoundaryDB.getXPath(bcid)

            if type_ == BoundaryType.VELOCITY_INLET.value:
                spec = self._db.getValue(xpath + '/velocityInlet/velocity/specification')
                if spec == VelocitySpecification.COMPONENT.value:
                    profile = self._db.getValue(xpath + '/velocityInlet/velocity/component/profile')
                    if profile == VelocityProfile.CONSTANT.value:
                        field[name] = self._constructFixedValue(
                            self._db.getVector(xpath + '/velocityInlet/velocity/component/constant'))
                    elif profile == VelocityProfile.SPATIAL_DISTRIBUTION.value:
                        field[name] = self._constructTimeVaryingMappedFixedValue(
                            self._rname, 'U', xpath + '/velocityInlet/velocity/component/spatialDistribution')
                    elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION.value:
                        field[name] = self._constructUniformFixedValue(
                            xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear',
                            self.TableType.TEMPORAL_VECTOR_LIST)
                elif spec == VelocitySpecification.MAGNITUDE.value:
                    profile = self._db.getValue(xpath + '/velocityInlet/velocity/magnitudeNormal/profile')
                    if profile == VelocityProfile.CONSTANT.value:
                        field[name] = self._constructSurfaceNormalFixedValue(
                            self._db.getValue(xpath + '/velocityInlet/velocity/magnitudeNormal/constant'))
                    elif profile == VelocityProfile.SPATIAL_DISTRIBUTION.value:
                        field[name] = self._constructTimeVaryingMappedFixedValue(
                            self._rname, 'U', xpath + '/velocityInlet/velocity/magnitudeNormal/spatialDistribution')
                    elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION.value:
                        field[name] = self._constructUniformNormalFixedValue(
                            xpath + '/velocityInlet/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear',
                            self.TableType.TEMPORAL_SCALAR_LIST)
            elif type_ == BoundaryType.FLOW_RATE_INLET.value:
                field[name] = self._constructFlowRateInletVelocity(xpath + '/flowRateInlet')
            elif type_ == BoundaryType.PRESSURE_INLET.value:
                field[name] = self._constructPressureInletOutletVelocity()
            elif type_ == BoundaryType.PRESSURE_OUTLET.value:
                field[name] = self._constructPressureInletOutletVelocity()
            elif type_ == BoundaryType.ABL_INLET.value:
                field[name] = self._constructAtmBoundaryLayerInletVelocity()
            elif type_ == BoundaryType.OPEN_CHANNEL_INLET.value:
                field[name] = self._constructVariableHeightFlowRateInletVelocity(
                    self._db.getValue(xpath + '/openChannelInlet/volumeFlowRate'))
            elif type_ == BoundaryType.OPEN_CHANNEL_OUTLET.value:
                field[name] = self._constructOutletPhaseMeanVelocity(
                    self._db.getValue(xpath + '/openChannelOutlet/meanVelocity'))
            elif type_ == BoundaryType.OUTFLOW.value:
                field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.FREE_STREAM.value:
                field[name] = self._constructFreestreamVelocity(xpath + '/freeStream')
            elif type_ == BoundaryType.FAR_FIELD_RIEMANN.value:
                field[name] = self._constructFarfieldRiemann(xpath + '/farFieldRiemann')
            elif type_ == BoundaryType.SUBSONIC_INFLOW.value:
                field[name] = self._constructSubsonicInflow(xpath + '/subsonicInflow')
            elif type_ == BoundaryType.SUBSONIC_OUTFLOW.value:
                field[name] = self._constructSubsonicOutflow(xpath + '/subsonicOutflow')
            elif type_ == BoundaryType.SUPERSONIC_INFLOW.value:
                field[name] = self._constructFixedValue(self._db.getVector(xpath + '/supersonicInflow/velocity'))
            elif type_ == BoundaryType.SUPERSONIC_OUTFLOW.value:
                field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.WALL.value:
                spec = self._db.getValue(xpath + '/wall/velocity/type')
                if spec == WallVelocityCondition.NO_SLIP.value:
                    field[name] = self._constructNoSlip()
                elif spec == WallVelocityCondition.SLIP.value:
                    field[name] = self._construcSlip()
                elif spec == WallVelocityCondition.MOVING_WALL.value:
                    field[name] = self._constructMovingWallVelocity()
                elif spec == WallVelocityCondition.ATMOSPHERIC_WALL.value:
                    field[name] = self._constructNoSlip()
                elif spec == WallVelocityCondition.TRANSLATIONAL_MOVING_WALL.value:
                    field[name] = self._constructFixedValue(
                        self._db.getVector(xpath + '/wall/velocity/translationalMovingWall/velocity'))
                elif spec == WallVelocityCondition.ROTATIONAL_MOVING_WALL.value:
                    field[name] = self._constructRotatingWallVelocity(xpath + '/wall/velocity/rotationalMovingWall')
            elif type_ == BoundaryType.THERMO_COUPLED_WALL.value:
                field[name] = self._constructNoSlip()
            elif type_ == BoundaryType.SYMMETRY.value:
                field[name] = self._constructSymmetry()
            elif type_ == BoundaryType.INTERFACE.value:
                spec = self._db.getValue(xpath + '/interface/mode')
                if spec == InterfaceMode.REGION_INTERFACE.value:
                    field[name] = self._constructNoSlip()
                else:
                    field[name] = self._constructCyclicAMI()
            elif type_ == BoundaryType.POROUS_JUMP.value:
                field[name] = self._constructCyclic()
            elif type_ == BoundaryType.FAN.value:
                field[name] = self._constructCyclic()
            elif type_ == BoundaryType.EMPTY.value:
                field[name] = self._constructEmpty()
            elif type_ == BoundaryType.CYCLIC.value:
                field[name] = self._constructCyclic()
            elif type_ == BoundaryType.WEDGE.value:
                field[name] = self._constructWedge()

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
                'massFlowRate': self._db.getValue(xpath + '/flowRate/massFlowRate')
            }

    def _constructPressureInletOutletVelocity(self):
        return {
            'type': 'pressureInletOutletVelocity',
            'value': ('uniform', self._initialValue)
        }

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
            'alpha': 'alpha.liquid',
            'flowRate': flowRate,
            'value': ('uniform', self._initialValue)
        }

    def _constructOutletPhaseMeanVelocity(self, Umean):
        return {
            'type': 'outletPhaseMeanVelocity',
            'alpha': 'alpha.liquid',
            'Umean': Umean
        }

    def _constructFreestreamVelocity(self, xpath):
        return {
            'type': 'freestreamVelocity',
            'U': self._db.getVector(xpath + '/streamVelocity')
        }

    def _constructNoSlip(self):
        # Can be set to 'slip' but for paraview set to 'fixedValue'
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
            'omega': self._db.getValue(xpath + '/speed'),
        }
