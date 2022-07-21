#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict

from coredb import coredb
from coredb.settings import Settings, CaseStatus
from openfoam.file_system import FileSystem


logger = logging.getLogger(__name__)


class PolyMeshLoader:
    @classmethod
    def load(cls):
        db = coredb.CoreDB()

        for entry in os.scandir(FileSystem.constantPath()):
            if entry.is_dir():
                rname = entry.name
                boundaryPath = FileSystem.boundaryFilePath(rname)
                if os.path.isfile(boundaryPath):
                    boundaryDict = cls.loadBoundary(boundaryPath)
                    if boundaryDict:
                        db.addRegion(rname)
                        for bname, boundary in boundaryDict.content.items():
                            db.addBoundaryCondition(rname, bname, boundary['type'])

                        cellZonesPath = FileSystem.cellZonesFilePath(rname)
                        if os.path.isfile(cellZonesPath):
                            cellZonesDict = cls.loadBoundary(cellZonesPath)
                            if cellZonesDict:
                                for czname, cellZone in cellZonesDict.content.items():
                                    cellLabels = cellZone['cellLabels']
                                    if cellLabels and cellLabels[len(cellLabels) - 1]:
                                        db.addCellZone(rname, czname)
                else:
                    logger.info(f'{rname} has no polyMesh({boundaryPath}), and is not added to regions')

        Settings.setStatus(CaseStatus.MESH_LOADED)

    @classmethod
    def loadBoundary(cls, path):
        try:
            return ParsedBoundaryDict(path)
        except Exception as ex:
            logger.warning(f'{path} is not boundary file: {ex}')
        return None
