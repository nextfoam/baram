#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict

from coredb import coredb
from openfoam.dictionary_file import DictionaryFile


logger = logging.getLogger(__name__)


class PolyMeshLoader:
    def load(self, dir):
        db = coredb.CoreDB()

        for entry in os.scandir(dir):
            if entry.is_dir():
                rname = entry.name
                polyMeshPath = os.path.join(entry.path, DictionaryFile.POLYMESH_DIRECTORY_NAME)
                boundaryPath = os.path.join(polyMeshPath, 'boundary')
                if os.path.isfile(boundaryPath):
                    boundaryDict = self.loadBoundary(boundaryPath)
                    if boundaryDict:
                        print(boundaryDict.content)
                        db.addRegion(rname)
                        for bname, boundary in boundaryDict.content.items():
                            db.addBoundaryCondition(rname, bname, boundary['type'])

                        cellZonesPath = os.path.join(polyMeshPath, 'cellZones')
                        if os.path.isfile(cellZonesPath):
                            cellZonesDict = self.loadBoundary(cellZonesPath)
                            if cellZonesDict:
                                print(cellZonesDict.content)

                                for zname, cellZone in cellZonesDict.content.items():
                                    cellLabels = cellZone['cellLabels']
                                    if cellLabels and cellLabels[len(cellLabels) - 1]:
                                        db.addCellZone(rname, zname)
                else:
                    logger.info(f'{rname} has no polyMesh({boundaryPath}), and is not added to regions')

    @classmethod
    def loadBoundary(cls, path):
        try:
            return ParsedBoundaryDict(path)
        except Exception as ex:
            logger.warning(f'{path} is not boundary file: {ex}')
        return None
