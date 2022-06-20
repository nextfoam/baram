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


class MeshObject:
    def __init__(self, id_, name, rname):
        """Constructs a mesh object (boundary or cell zone)

        Args:
            id_: object ID
            name: object name
            rname: name of the region containing the object
        """
        self._id = id_
        self._name = name
        self._rname = rname

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def rname(self):
        return self._rname

    def toText(self):
        return f'{self._rname} / {self._name}'


class CellZoneDB:
    CELL_ZONE_CONDITIONS_XPATH = './/cellZones'
    OPERATING_CONDITIONS_XPATH = './/operatingConditions'
    NAME_FOR_ALL = 'All'

    _db = coredb.CoreDB()
    _cellZonesForSelector = None

    @classmethod
    def getXPath(cls, czid):
        return f'{cls.CELL_ZONE_CONDITIONS_XPATH}/cellZone[@czid="{czid}"]'

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
                    name = cellZone[CellZoneListIndex.NAME.value]
                    if name != cls.NAME_FOR_ALL:
                        cls._cellZonesForSelector.append(
                            MeshObject(str(cellZone[CellZoneListIndex.ID.value]), name, region))

        return cls._cellZonesForSelector
