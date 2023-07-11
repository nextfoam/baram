#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import asyncio

from libbaram import utils


class FileSystem:
    CASE_DIRECTORY_NAME = 'case'
    CONSTANT_DIRECTORY_NAME = 'constant'
    BOUNDARY_CONDITIONS_DIRECTORY_NAME = '0'
    SYSTEM_DIRECTORY_NAME = 'system'
    POLY_MESH_DIRECTORY = CONSTANT_DIRECTORY_NAME + '/polyMesh'
    REGION_PROPERTIES_FILE_NAME = 'regionProperties'
    FOAM_FILE_NAME = 'baram.foam'
    TRI_SURFACE_DIRECTORY = CONSTANT_DIRECTORY_NAME + '/triSurface'

    def __init__(self, path):
        self._casePath = None

        self._setCaseRoot(path / self.CASE_DIRECTORY_NAME)

    def caseRoot(self):
        return self._casePath

    def createCase(self, src):
        if self._casePath.exists():
            utils.rmtree(self._casePath)

        shutil.copytree(src, self._casePath)

    def triSurfacePath(self):
        return self._triSurfacePath

    async def copyTriSurfaceFrom(self, srcPath, fileName):
        await asyncio.to_thread(shutil.copyfile, srcPath, self._triSurfacePath / fileName)

    def _setCaseRoot(self, path):
        self._casePath = path
        self._triSurfacePath = self._casePath / self.TRI_SURFACE_DIRECTORY
