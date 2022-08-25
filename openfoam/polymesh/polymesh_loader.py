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
        """
        Load regions and boundaries from srcPath, and return directory's path to copy.

        Args:
            srcPath: Full path of the directory selected by the user.

        Returns:
            For multi-region meshes, full path to copy to 'constant'.
            For single-region meshes, full path to copy to 'constant/polyMesh'.

        """
        db = coredb.CoreDB()

        boundaries = {}
        if not srcPath:
            srcPath = FileSystem.constantPath(FileSystem.POLY_MESH_DIRECTORY_NAME)
        path = srcPath

        regions = cls.loadRegions(srcPath)
        if regions is None:
            # single region
            regions = ['']

            if not FileSystem.isPolyMesh(path):
                path = srcPath / 'polyMesh'
                if not FileSystem.isPolyMesh(path):
                    raise FileLoadingError('Mesh directory not found.')

            boundaryDict = cls.loadBoundaryDict(path / 'boundary')
            boundaries[''] = [(bname, boundary['type']) for bname, boundary in boundaryDict.content.items()]
        else:
            # multi region
            for rname in regions:
                boundaryDict = cls.loadBoundaryDict(path / rname / FileSystem.POLY_MESH_DIRECTORY_NAME / 'boundary')
                boundaries[rname] = [(bname, boundary['type']) for bname, boundary in boundaryDict.content.items()]

        for rname in regions:
            db.addRegion(rname)
            for bcname, bctype in boundaries[rname]:
                db.addBoundaryCondition(rname, bcname, bctype)

        return path

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

        return None

    @classmethod
    def loadBoundaryDict(cls, path, listLengthUnparsed=None):
        return ParsedBoundaryDict(path, listLengthUnparsed=listLengthUnparsed, treatBinaryAsASCII=True)
