#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.boundary.boundary_data import BoundaryData
from baramFlow.base.cell_zone.cell_zone import CellZoneData
from baramFlow.base.region.poly_mesh import PolyMeshRegion
from baramFlow.base.region.region_patch import RegionInitializationPatch
from baramFlow.base.region.regions_cache import regionCache
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.coredb import CoreDB
from baramFlow.coredb.coredb_writer import CoreDBWriter

REGIONS_XPATH = '/regions'


class RegionService:
    @staticmethod
    def getBoundary(bcid: str):
        RegionService.reloadBoundary(bcid)    # ToDo: Delete if database synchronization is guaranteed.
        return regionCache.boundaries[bcid]

    @staticmethod
    def getBoundaries():
        return regionCache.boundaries.values()

    @staticmethod
    def getBoundariesIn(rname):
        return regionCache.regions[rname].boundaries

    @staticmethod
    def getCellZone(czid: str):
        RegionService.reloadCellZone(czid)    # ToDo: Delete if database synchronization is guaranteed.
        return regionCache.cellZones[czid]

    @staticmethod
    def getCellZones():
        return regionCache.cellZones.values()

    @staticmethod
    def isMultiRegion():
        return len(regionCache.regions) > 1

    @staticmethod
    def reloadBoundary(bcid: str):
        new = BoundaryData.fromElement(CoreDB().getElement(BoundaryDB.getXPath(bcid)))
        regionCache.boundaries[bcid].boundary = new

    @staticmethod
    def reloadCellZone(czid: str):
        new = CellZoneData.fromElement(CoreDB().getElement(CellZoneDB.getXPath(czid)))
        regionCache.cellZones[czid].configurations = new

    @staticmethod
    def matches(vtkMesh: dict):
        if regionCache is None:
            return False

        regions = regionCache.regions
        if set(regions) != set(rname for rname in vtkMesh if 'boundary' in vtkMesh[rname]):
            return False

        for rname, region in regions.items():
            if set(region.getBoundaryNames()) != set(vtkMesh[rname]['boundary'].keys()):
                return False

            if 'zones' in vtkMesh[rname] and 'cellZones' in vtkMesh[rname]['zones']:
                newCellZones = set(vtkMesh[rname]['zones']['cellZones'].keys())
            else:
                newCellZones = {}

            if set(region.getCellZoneNames(includeEntireZone=False)) != newCellZones:
                return False

        return True

    @staticmethod
    def clear():
        regionCache.clear()

    @staticmethod
    def replace(data: list[PolyMeshRegion]):
        regionCache.replace(data)

        with CoreDB() as db:
            db.replaceElement(REGIONS_XPATH, regionCache.toElement())
            db.increaseConfigCount()

    @staticmethod
    def updatePolyMeshData(polyMeshBoundaries: dict):
        regionCache.updatePolyMeshData(polyMeshBoundaries)

    @staticmethod
    def updateInitialization(patches: list[RegionInitializationPatch], writer: CoreDBWriter = None):
        with CoreDB() as db:
            for p in patches:
                p.applyToDB(db)

            if writer is not None:
                writer.updateInDB(db)

            # db.increaseConfigCount()
