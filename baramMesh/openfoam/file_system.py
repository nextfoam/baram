#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import shutil
from typing import Optional
from pathlib import Path

import asyncio

from libbaram.openfoam.polymesh import isPolyMesh
from libbaram.utils import rmtree
from libbaram.openfoam.constants import Directory, CASE_DIRECTORY_NAME, FOAM_FILE_NAME


def makeDir(parent, directory, clear=False) -> Path:
    path = parent / directory

    if clear and path.exists():
        rmtree(path)

    path.mkdir(parents=True, exist_ok=True)

    return path


class FileSystem:
    def __init__(self, path):
        self._casePath: Optional[Path] = None
        self._systemPath: Optional[Path] = None
        self._constantPath: Optional[Path] = None
        self._triSurfacePath: Optional[Path] = None

        self._setCaseRoot(path / CASE_DIRECTORY_NAME)

    def caseRoot(self):
        return self._casePath

    def constantPath(self, rname=None):
        return self._constantPath / rname if rname else self._constantPath

    def triSurfacePath(self):
        return self._triSurfacePath

    def polyMeshPath(self, rname=None):
        return self.constantPath(rname) / Directory.POLY_MESH_DIRECTORY_NAME

    def boundaryFilePath(self, rname=None):
        return self.polyMeshPath(rname) / Directory.BOUNDARY_FILE_NAME

    def foamFilePath(self):
        return self._casePath / FOAM_FILE_NAME

    def processorPath(self, no, checkExistence=True):
        path = self._casePath / f'processor{no}'

        return path if not checkExistence or path.is_dir() else None

    def timePath(self, time, processorNo=None):
        return self._casePath / str(time) if processorNo is None else self.processorPath(processorNo, False) / str(time)

    def timePathExists(self, time, parallel=False):
        return self.timePath(time, 0 if parallel else None).exists()

    def hasPolyMesh(self, time, parallel=False):
        timePath = self.timePath(time, 0 if parallel else None)
        if not timePath.is_dir():
            return False

        return isPolyMesh(timePath / Directory.POLY_MESH_DIRECTORY_NAME)

    def latestTime(self, parent: Optional[Path] = None) -> str:
        times = self.times(parent)
        if len(times) == 0:
            return '0'

        return max(times, key=lambda x: float(x))

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
            rmtree(self._casePath)

        shutil.copytree(src, self._casePath)

        self._systemPath = self._casePath / Directory.SYSTEM_DIRECTORY_NAME
        self._constantPath = makeDir(self._casePath, Directory.CONSTANT_DIRECTORY_NAME)
        self._triSurfacePath = makeDir(self._constantPath, Directory.TRI_SURFACE_DIRECTORY_NAME)

        makeDir(self._casePath, Directory.BOUNDARY_CONDITIONS_DIRECTORY_NAME)
        
    async def createRegionSystemDirectory(self, rname):
        path = makeDir(self._systemPath, rname)
        await asyncio.to_thread(shutil.copyfile, self._systemPath / 'fvSchemes', path / 'fvSchemes')
        await asyncio.to_thread(shutil.copyfile, self._systemPath / 'fvSolution', path / 'fvSolution')

    def saveAs(self, path):
        shutil.copytree(self._casePath, path / CASE_DIRECTORY_NAME, copy_function=shutil.copyfile)

    async def copyTriSurfaceFrom(self, srcPath, fileName):
        targetFile = self._triSurfacePath / fileName
        await asyncio.to_thread(shutil.copyfile, srcPath, targetFile)

        return targetFile

    async def copyTimeDirectory(self, srcTime, destTime, processorNo=None):
        srcPath = self.timePath(srcTime, processorNo)
        if not srcPath.is_dir():
            return

        destPath = self.timePath(destTime, processorNo)
        await asyncio.to_thread(shutil.copytree, srcPath, destPath)

    def _setCaseRoot(self, path):
        self._casePath = path
        self._constantPath = self._casePath / Directory.CONSTANT_DIRECTORY_NAME
        self._triSurfacePath = self._constantPath / Directory.TRI_SURFACE_DIRECTORY_NAME


