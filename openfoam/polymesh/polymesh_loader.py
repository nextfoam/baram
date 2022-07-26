#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict, ParsedParameterFile

from coredb import coredb
from coredb.settings import Settings, CaseStatus
from openfoam.file_system import FileSystem


logger = logging.getLogger(__name__)


class PolyMeshLoader:
    @classmethod
    def load(cls):
        db = coredb.CoreDB()

        regions = cls.loadRegions()
        boundaries = {}
        cellZones = []

        for rname in regions:
            boundaryDict = cls.loadBoundaryDict(FileSystem.boundaryFilePath(rname))
            boundaries[rname] = [(bname, boundary['type']) for bname, boundary in boundaryDict.content.items()]
            cellZonesPath = FileSystem.cellZonesFilePath(rname)
            if os.path.isfile(cellZonesPath):
                cellZonesDict = cls.loadBoundaryDict(cellZonesPath, 10)
                if cellZonesDict:
                    for czname, cellZone in cellZonesDict.content.items():
                        cellLabels = cellZone['cellLabels']
                        if cellLabels and cellLabels[len(cellLabels) - 1]:
                            cellZones.append((rname, czname))

        for rname in regions:
            db.addRegion(rname)
            for bname, btype in boundaries[rname]:
                db.addBoundaryCondition(rname, bname, btype)

        for rname, czname in cellZones:
            db.addCellZone(rname, czname)

        Settings.setStatus(CaseStatus.MESH_LOADED)

    @classmethod
    def loadRegions(cls):
        fileName = FileSystem.constantPath('regionProperties')
        if os.path.isfile(fileName):
            regions = []
            regionsDict = ParsedParameterFile(fileName).content['regions']
            for i in range(1, len(regionsDict), 2):
                for region in regionsDict[i]:
                    regions.append(region)

            if regions:
                return regions
            else:
                raise RuntimeError

        return ['']

    @classmethod
    def loadBoundaryDict(cls, path, listLengthUnparsed=None):
        return ParsedBoundaryDict(path, listLengthUnparsed=listLengthUnparsed)
