#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from coredb import coredb
from coredb.material_db import MaterialDB


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


class RegionDB:
    @classmethod
    def getXPath(cls, rname):
        return f'.//region[name="{rname}"]'

    @classmethod
    def getPhase(cls, rname):
        return MaterialDB.getPhase(coredb.CoreDB().getValue(cls.getXPath(rname) + '/material'))


class CellZoneDB:
    CELL_ZONE_CONDITIONS_XPATH = './/cellZones'
    NAME_FOR_ALL = 'All'

    _cellzones = None

    @classmethod
    def getXPath(cls, czid):
        return f'{cls.CELL_ZONE_CONDITIONS_XPATH}/cellZone[@czid="{czid}"]'

    @classmethod
    def getCellZoneName(cls, czid):
        return coredb.CoreDB().getValue(cls.getXPath(czid) + '/name')

    @classmethod
    def getCellZoneRegion(cls, czid):
        return coredb.CoreDB().getValue(cls.getXPath(czid) + '/../../name')

    @classmethod
    def getCellZones(cls):
        db = coredb.CoreDB()
        
        if not cls._cellzones:
            cls._cellzones = []

            for region in db.getRegions():
                for cellZone in db.getCellZones(region):
                    name = cellZone[CellZoneListIndex.NAME.value]
                    if name != cls.NAME_FOR_ALL:
                        cls._cellzones.append(
                            MeshObject(str(cellZone[CellZoneListIndex.ID.value]), name, region))

        return cls._cellzones
