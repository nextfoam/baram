#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import shutil
from typing import Optional
from pathlib import Path

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

    def processorPath(self, no):
        path = (self._casePath / f'processor{no}')

        return path if path.is_dir() else None

    def timePath(self, time):
        return self._casePath / str(time)

    def times(self, parent: Optional[Path] = None):
        if parent is None:
            parent = self.processorPath(0)
            if parent is None:
                parent = self._casePath

        times = []
        for f in parent.iterdir():
            if not f.is_dir():
                continue

            if re.fullmatch(r'^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$', f.name):
                times.append(f.name)

        return times

    def processorFolders(self):
        return list(self._casePath.glob('processor[0-9]*'))

    def numberOfProcessorFolders(self):
        return len(self.processorFolders())

    def createCase(self, src):
        if self._casePath.exists():
            utils.rmtree(self._casePath)

        shutil.copytree(src, self._casePath)

        self._constantPath = makeDir(self._casePath, self.CONSTANT_DIRECTORY_NAME)
        self._triSurfacePath = makeDir(self._constantPath, self.TRI_SURFACE_DIRECTORY_NAME)
        makeDir(self._casePath, '0')

    async def copyTriSurfaceFrom(self, srcPath, fileName):
        targetFile = self._triSurfacePath / fileName
        await asyncio.to_thread(shutil.copyfile, srcPath, targetFile)

        return targetFile

    async def copyTimeDrectory(self, srcTime, destTime):
        srcPath = self.timePath(srcTime)
        if any(srcPath.iterdir()):
            await asyncio.to_thread(shutil.copytree, self.timePath(srcTime), self.timePath(destTime))
            return True

        return False

    def _setCaseRoot(self, path):
        self._casePath = path
        self._constantPath = self._casePath / self.CONSTANT_DIRECTORY_NAME
        self._triSurfacePath = self._constantPath / self.TRI_SURFACE_DIRECTORY_NAME
