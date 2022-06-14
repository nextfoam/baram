#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from coredb import coredb


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


class ListIndex(Enum):
    ID = 0
    NAME = auto()
    TYPE = auto()


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
    ROTATIONAL_MOVING_WALL = "RotationalMovingWall"


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

    _db = coredb.CoreDB()
    _boundariesForSelector = None

    @classmethod
    def getBoundaryXPath(cls, bcid):
        return f'{cls.BOUNDARY_CONDITIONS_XPATH}/boundaryCondition[@bcid="{bcid}"]'

    @classmethod
    def getBoundaryName(cls, bcid):
        return cls._db.getValue(BoundaryDB.getBoundaryXPath(bcid) + '/name')

    @classmethod
    def getBoundaryRegion(cls, bcid):
        return cls._db.getValue(BoundaryDB.getBoundaryXPath(bcid) + '/../../name')

    @classmethod
    def getBoundariesForSelector(cls):
        if cls._boundariesForSelector is None:
            cls._boundariesForSelector = []

            for region in cls._db.getRegions():
                for boundary in cls._db.getBoundaryConditions(region):
                    cls._boundariesForSelector.append((
                        f'{boundary[ListIndex.NAME.value]} / {region}',
                        boundary[ListIndex.NAME.value],
                        boundary[ListIndex.ID.value]
                    ))

        return cls._boundariesForSelector

    @classmethod
    def getCyclicAMIBoundaries(cls, bcidToExcept):
        boundaries = []

        for region in cls._db.getRegions():
            for boundary in cls._db.getBoundaryConditions(region):
                bcid = boundary[ListIndex.ID.value]
                if bcid != bcidToExcept:
                        #and cls._db.getValue(cls.getBoundaryXPath(bcid) + '/geometricalType') == "cyclic":
                    boundaries.append((
                        f'{boundary[ListIndex.NAME.value]} / {region}',
                        boundary[ListIndex.NAME.value],
                        bcid
                    ))

        return boundaries
