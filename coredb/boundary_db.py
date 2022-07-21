#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from coredb import coredb
from coredb.cell_zone_db import MeshObject


class BoundaryType(Enum):
    # Inlet
    VELOCITY_INLET	    = "velocityInlet"
    FLOW_RATE_INLET	    = "flowRateInlet"
    PRESSURE_INLET	    = "pressureInlet"
    ABL_INLET	        = "ablInlet"
    OPEN_CHANNEL_INLET  = "openChannelInlet"
    FREE_STREAM	        = "freeStream"
    FAR_FIELD_RIEMANN	= "farFieldRiemann"
    SUBSONIC_INFLOW	    = "subsonicInflow"
    SUPERSONIC_INFLOW	= "supersonicInflow"
    # Outlet
    PRESSURE_OUTLET	    = "pressureOutlet"
    OPEN_CHANNEL_OUTLET = "openChannelOutlet"
    OUTFLOW	            = "outflow"
    SUBSONIC_OUTFLOW	= "subsonicOutflow"
    SUPERSONIC_OUTFLOW	= "supersonicOutflow"
    # Wall
    WALL	            = "wall"
    THERMO_COUPLED_WALL	= "thermoCoupledWall"
    POROUS_JUMP	        = "porousJump"
    FAN	                = "fan"
    # Internal
    SYMMETRY	        = "symmetry"
    INTERFACE	        = "interface"
    EMPTY	            = "empty"
    CYCLIC	            = "cyclic"
    WEDGE	            = "wedge"


class VelocitySpecification(Enum):
    COMPONENT = "component"
    MAGNITUDE = "magnitudeNormal"


class VelocityProfile(Enum):
    CONSTANT = "constant"
    SPATIAL_DISTRIBUTION = "spatialDistribution"
    TEMPORAL_DISTRIBUTION = "temporalDistribution"


class FlowRateInletSpecification(Enum):
    VOLUME_FLOW_RATE = "volumeFlowRate"
    MASS_FLOW_RATE = "massFlowRate"


class WallVelocityCondition(Enum):
    NO_SLIP = "noSlip"
    SLIP = "slip"
    MOVING_WALL = "movingWall"
    ATMOSPHERIC_WALL = "atmosphericWall"
    TRANSLATIONAL_MOVING_WALL = "translationalMovingWall"
    ROTATIONAL_MOVING_WALL = "rotationalMovingWall"


class WallTemperature(Enum):
    ADIABATIC = "adiabatic"
    CONSTANT_TEMPERATURE = "constantTemperature"
    CONSTANT_HEAT_FLUX = "constantHeatFlux"
    CONVECTION = "convection"


class InterfaceMode(Enum):
    INTERNAL_INTERFACE = "internalInterface"
    ROTATIONAL_PERIODIC = "rotationalPeriodic"
    TRANSLATIONAL_PERIODIC = "translationalPeriodic"
    REGION_INTERFACE = "regionInterface"


class SpalartAllmarasSpecification(Enum):
    MODIFIED_TURBULENT_VISCOSITY = "modifiedTurbulentViscosity"
    TURBULENT_VISCOSITY_RATIO = "turbulentViscosityRatio"


class KEpsilonSpecification(Enum):
    K_AND_EPSILON = "kAndEpsilon"
    INTENSITY_AND_VISCOSITY_RATIO = "intensityAndViscosityRatio"


class KOmegaSpecification(Enum):
    K_AND_OMEGA = "kAndOmega"
    INTENSITY_AND_VISCOSITY_RATIO = "intensityAndViscosityRatio"


class TemperatureProfile(Enum):
    CONSTANT = "constant"
    SPATIAL_DISTRIBUTION = "spatialDistribution"
    TEMPORAL_DISTRIBUTION = "temporalDistribution"


class TemperatureTemporalDistribution(Enum):
    PIECEWISE_LINEAR = "piecewiseLinear"
    POLYNOMIAL = "polynomial"


class BoundaryDB:
    BOUNDARY_CONDITIONS_XPATH = './/boundaryConditions'
    ABL_INLET_CONDITIONS_XPATH = './/atmosphericBoundaryLayer'

    _boundariesForSelector = None
    _boundariesForSelectorWithNone = None

    @classmethod
    def getXPath(cls, bcid):
        return f'{cls.BOUNDARY_CONDITIONS_XPATH}/boundaryCondition[@bcid="{bcid}"]'

    @classmethod
    def getBoundaryName(cls, bcid):
        return coredb.CoreDB().getValue(cls.getXPath(bcid) + '/name')

    @classmethod
    def getBoundaryRegion(cls, bcid):
        return coredb.CoreDB().getValue(cls.getXPath(bcid) + '/../../name')

    @classmethod
    def getBoundariesForSelector(cls):
        db = coredb.CoreDB()

        if not cls._boundariesForSelector:
            cls._boundariesForSelector = []

            for region in db.getRegions():
                for bcid, bcname, ptype in db.getBoundaryConditions(region):
                    cls._boundariesForSelector.append(
                        MeshObject(str(bcid), bcname, region))

        return cls._boundariesForSelector

    @classmethod
    def getCyclicAMIBoundaries(cls, bcidToExcept):
        db = coredb.CoreDB()

        boundaries = []
        for region in db.getRegions():
            for bcid, bcname, ptype in db.getBoundaryConditions(region):
                if bcid != bcidToExcept:
                        #and db.getValue(cls.getBoundaryXPath(bcid) + '/geometricalType') == "cyclic":
                    boundaries.append(MeshObject(str(bcid), bcname, region))

        return boundaries
