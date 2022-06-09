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


class ListItemIndex(Enum):
    ID = 0
    NAME = auto()
    TYPE = auto()


class BoundaryDB:
    BOUNDARY_CONDITIONS_XPATH = './/boundaryConditions'

    _db = coredb.CoreDB()
    _boundariesForSelector = None

    @classmethod
    def getBoundaryXPath(cls, bcid):
        return f'{cls.BOUNDARY_CONDITIONS_XPATH}/boundaryCondition[@bcid="{bcid}"]'

    @classmethod
    def getBoundariesForSelector(cls):
        if cls._boundariesForSelector is None:
            cls._boundariesForSelector = []

            for region in cls._db.getRegions():
                for boundary in cls._db.getBoundaryConditions(region):
                    cls._boundariesForSelector.append((
                        f'{boundary[ListItemIndex.NAME.value]} / {region}',
                        boundary[ListItemIndex.NAME.value],
                        boundary[ListItemIndex.ID.value]
                    ))

        return cls._boundariesForSelector
