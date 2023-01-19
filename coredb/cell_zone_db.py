#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from coredb import coredb
from view.widgets.multi_selector_dialog import SelectorItem


class ZoneType(Enum):
    NONE = 'none'
    MRF = 'mrf'
    POROUS = 'porous'
    SLIDING_MESH = 'slidingMesh'
    ACTUATOR_DISK = 'actuatorDisk'


class PorousZoneModel(Enum):
    DARCY_FORCHHEIMER = 'darcyForchheimer'
    POWER_LAW = 'powerLaw'


class SpecificationMethod(Enum):
    VALUE_PER_UNIT_VOLUME = 'valuePerUnitVolume'
    VALUE_FOR_ENTIRE_CELL_ZONE = 'valueForEntireCellZone'


class TemporalProfileType(Enum):
    CONSTANT = 'constant'
    PIECEWISE_LINEAR = 'piecewiseLinear'
    POLYNOMIAL = 'polynomial'


class CellZoneDB:
    CELL_ZONE_CONDITIONS_XPATH = './/cellZones'
    NAME_FOR_REGION = 'All'

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
    def getCellZoneText(cls, czid):
        rname = cls.getCellZoneRegion(czid)
        r = '' if rname == '' else rname + ':'
        return f'{r}{cls.getCellZoneName(czid)}' if czid else ''

    @classmethod
    def getCellZoneType(cls, czid):
        return coredb.CoreDB().getValue(cls.getXPath(czid) + '/zoneType')

    @classmethod
    def isRegion(cls, czname):
        return czname == cls.NAME_FOR_REGION

    @classmethod
    def getCellZoneSelectorItems(cls):
        db = coredb.CoreDB()

        if not cls._cellzones:
            cls._cellzones = []

            for rname in db.getRegions():
                r = '' if rname == '' else rname + ':'
                for czid, czname in db.getCellZones(rname):
                    # if czname != cls.NAME_FOR_ALL:
                    cls._cellzones.append(SelectorItem(f'{r}{czname}', czname, str(czid)))

        return cls._cellzones
