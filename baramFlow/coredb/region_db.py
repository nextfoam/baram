#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB


DEFAULT_REGION_NAME = 'region0'


class RegionDB:
    @classmethod
    def getXPath(cls, rname):
        return f'.//region[name="{rname}"]'

    @classmethod
    def getPhase(cls, rname):
        return MaterialDB.getPhase(coredb.CoreDB().getValue(cls.getXPath(rname) + '/material'))

    @classmethod
    def getMaterial(cls, rname):
        return coredb.CoreDB().getValue(cls.getXPath(rname) + '/material')

    @classmethod
    def getSecondaryMaterials(cls, rname):
        return coredb.CoreDB().getValue(cls.getXPath(rname) + '/secondaryMaterials').split()

    @classmethod
    def getNumberOfRegions(cls):
        return len(coredb.CoreDB().getRegions())


