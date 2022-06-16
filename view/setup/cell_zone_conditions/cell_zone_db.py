#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from coredb import coredb


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
    CELL_ZONE_CONDITIONS_XPATH = './/cellZones'

    _db = coredb.CoreDB()
    _cellZonesForSelector = None

    @classmethod
    def getXPath(cls, czid):
        return f'{cls.CELL_ZONE_CONDITIONS_XPATH}/cellZone[@czid="{czid}"]'

    @classmethod
    def getXPathWithRegion(cls, rname, czid):
        return f'.//region[name="{rname}"]/cellZones/cellZone[@czid="{czid}"]'

    @classmethod
    def getRegionXPath(cls, rname):
        return f'.//region[name="{rname}"]'

    @classmethod
    def getCellZoneName(cls, czid):
        return cls._db.getValue(cls.getXPath(czid) + '/name')

    @classmethod
    def getCellZoneRegion(cls, czid):
        return cls._db.getValue(cls.getXPath(czid) + '/../../name')

    @classmethod
    def getCellZonesForSelector(cls):
        if cls._cellZonesForSelector is None:
            cls._cellZonesForSelector = []

            for region in cls._db.getRegions():
                for cellZone in cls._db.getCellZones(region):
                    czid = cellZone[CellZoneListIndex.ID.value]
                    if czid != 1:
                        name = cellZone[CellZoneListIndex.NAME.value]
                        cls._cellZonesForSelector.append((f'{name} / {region}', name, str(czid)))

        return cls._cellZonesForSelector
