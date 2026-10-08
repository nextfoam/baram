#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.cell_zone.cell_zone import CellZoneData
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.coredb import _CoreDB
from baramFlow.services.region.region_service import RegionService


class CellZoneService:
    @staticmethod
    def getCellZone(czid: str):
        return RegionService.getCellZone(czid)

    @staticmethod
    def getCellZones():
        return RegionService.getCellZones()

    @staticmethod
    def updateCellZoneInDB(db: _CoreDB, czid: str, data: CellZoneData):
        db.replaceElement(CellZoneDB.getXPath(czid) + '/sourceTerms', data.sourceTerms.toElement())
        db.increaseConfigCount()

        # ToDo: Update entire configurations if databas synchronization is guaranteed.
        RegionService.getCellZone(czid).configurations.sourceTerms = data.sourceTerms
