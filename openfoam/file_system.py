#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil

import asyncio

from libbaram import utils


def makeDir(parent, directory):
    path = parent / directory
    path.mkdir(parents=True, exist_ok=True)
    return path


class FileSystem:
    CASE_DIRECTORY_NAME = 'case'
    CONSTANT_DIRECTORY_NAME = 'constant'
    BOUNDARY_CONDITIONS_DIRECTORY_NAME = '0'
    SYSTEM_DIRECTORY_NAME = 'system'
    REGION_PROPERTIES_FILE_NAME = 'regionProperties'
    FOAM_FILE_NAME = 'baram.foam'
    TRI_SURFACE_DIRECTORY_NAME = 'triSurface'
    POLY_MESH_DIRECTORY_NAME = 'polyMesh'
    BOUNDARY_FILE_NAME = 'boundary'

    def __init__(self, path):
        self._casePath = None
        self._constantPath = None
        self._triSurfacePath = None

        self._setCaseRoot(path / self.CASE_DIRECTORY_NAME)

    def caseRoot(self):
        return self._casePath

    def constantPath(self, rname=None):
        return self._constantPath / rname if rname else self._constantPath

    def triSurfacePath(self):
        return self._triSurfacePath

    def polyMeshPath(self, rname=None):
        return self.constantPath(rname) / self.POLY_MESH_DIRECTORY_NAME

    def boundaryFilePath(self, rname=None):
        return self.constantPath(rname) / self.POLY_MESH_DIRECTORY_NAME / 'boundary'

    def foamFilePath(self):
        return self._casePath / self.FOAM_FILE_NAME

    def createCase(self, src):
        if self._casePath.exists():
            utils.rmtree(self._casePath)

        shutil.copytree(src, self._casePath)

        self._constantPath = makeDir(self._casePath, self.CONSTANT_DIRECTORY_NAME)
        self._triSurfacePath = makeDir(self._constantPath, self.TRI_SURFACE_DIRECTORY_NAME)

    async def copyTriSurfaceFrom(self, srcPath, fileName):
        targetFile = self._triSurfacePath / fileName
        await asyncio.to_thread(shutil.copyfile, srcPath, targetFile)

        return targetFile

    def _setCaseRoot(self, path):
        self._casePath = path
        self._constantPath = self._casePath / self.CONSTANT_DIRECTORY_NAME
        self._triSurfacePath = self._constantPath / self.TRI_SURFACE_DIRECTORY_NAME
