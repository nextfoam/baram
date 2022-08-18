#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict, ParsedParameterFile

from coredb import coredb
from openfoam.file_system import FileSystem, FileLoadingError


logger = logging.getLogger(__name__)


class PolyMeshLoader:
    @classmethod
    async def loadBoundaries(cls, srcPath):
        db = coredb.CoreDB()

        regions = cls.loadRegions(srcPath)
        boundaries = {}

        for rname in regions:
            boundaryPath = (srcPath / rname if rname else srcPath) / FileSystem.POLY_MESH_DIRECTORY_NAME / 'boundary'
            boundaryDict = cls.loadBoundaryDict(boundaryPath)
            boundaries[rname] = [(bname, boundary['type']) for bname, boundary in boundaryDict.content.items()]

        for rname in regions:
            db.addRegion(rname)
            for bname, btype in boundaries[rname]:
                db.addBoundaryCondition(rname, bname, btype)

    @classmethod
    def loadRegions(cls, srcPath):
        fileName = srcPath / FileSystem.REGION_PROPERTIES_FILE_NAME
        if fileName.is_file():
            regions = []
            regionsDict = ParsedParameterFile(fileName).content['regions']
            for i in range(1, len(regionsDict), 2):
                for region in regionsDict[i]:
                    regions.append(region)

            if regions:
                return regions
            else:
                raise FileLoadingError('Failed to load regionProperties file.')

        return ['']

    @classmethod
    def loadBoundaryDict(cls, path, listLengthUnparsed=None):
        return ParsedBoundaryDict(path, listLengthUnparsed=listLengthUnparsed, treatBinaryAsASCII=True)
