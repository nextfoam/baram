#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto


class CellZoneListIndex(Enum):
    ID = 0
    NAME = auto()


class ZoneType(Enum):
    NONE = "none"
    MRF = "mrf"
    POROUS = "porous"
    SLIDING_MESH = "slidingMesh"
    ACTUATOR_DISK = "actuatorDisk"


class PorousZoneModel(Enum):
    DARCY_FORCHHEIMER = "darcyForchheimer"
    POWER_LAW = "powerLaw"


class SpecificationMethod(Enum):
    VALUE_PER_UNIT_VOLUME = 'valuePerUnitVolume'
    VALUE_FOR_ENTIRE_CELL_ZONE = 'valueForEntireCellZone'


class TemporalProfileType(Enum):
    CONSTANT = 'constant'
    PIECEWISE_LINEAR = 'piecewiseLinear'
    POLYNOMIAL = 'polynomial'


class CellZoneDB:
    @classmethod
    def getXPath(cls, rname, czid):
        return f'.//region[name="{rname}"]/cellZones/cellZone[@czid="{czid}"]'

    @classmethod
    def getRegionXPath(cls, rname):
        return f'.//region[name="{rname}"]'
