#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import qasync
import shutil

from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from libbaram import utils
from libbaram.openfoam.constants import CASE_DIRECTORY_NAME, Directory
from libbaram.openfoam.polymesh import isPolyMesh
from libbaram.run import RunParallelUtility, RunUtility

from baramFlow.coredb.project import Project
from baramFlow.mesh.flument_to_foam_control import FluentMeshConverter
from baramFlow.openfoam import parallel
from baramFlow.openfoam.constant.region_properties import RegionProperties
from baramFlow.openfoam.file_system import FileSystem, FileLoadingError


logger = logging.getLogger(__name__)


class MeshType(Enum):
    POLY_MESH = auto()
    FLUENT = auto()
    STAR_CCM = auto()
    GMSH = auto()
    IDEAS = auto()
    NAMS_PLOT3D = auto()


OPENFOAM_MESH_CONVERTERS = {
    MeshType.POLY_MESH: None,
    MeshType.FLUENT: ('fluentMeshToFoam', '-writeSets', '-writeZones'),
    MeshType.STAR_CCM: ('ccmToFoam',),
    MeshType.GMSH: ('gmshToFoam',),
    MeshType.IDEAS: ('ideasUnvToFoam',),
    MeshType.NAMS_PLOT3D: ('plot3dToFoam',),
}


class MeshManager(QObject):
    progress = Signal(str)

    def __init__(self):
        super().__init__()

        self._process = None

    @qasync.asyncSlot()
    async def scale(self, x, y, z):
        caseRoot = FileSystem.caseRoot()
        cm = RunParallelUtility('transformPoints', '-allRegions', '-scale', f'({x} {y} {z})',
                                '-case', caseRoot, cwd=caseRoot, parallel=parallel.getEnvironment())
        await cm.start()
        result = await cm.wait()

        if result == 0 and parallel.getNP() > 1:  # Process the mesh in constant folder too.
            cm = RunUtility('transformPoints', '-allRegions', '-scale', f'({x} {y} {z})',
                            '-case', caseRoot, cwd=caseRoot)

            await cm.start()
            result = await cm.wait()

        return result

    @qasync.asyncSlot()
    async def translate(self, x, y, z):
        caseRoot = FileSystem.caseRoot()
        cm = RunParallelUtility('transformPoints', '-allRegions', '-translate', f'({x} {y} {z})',
                                '-case', caseRoot, cwd=caseRoot, parallel=parallel.getEnvironment())
        await cm.start()
        result = await cm.wait()

        if result == 0 and parallel.getNP() > 1:  # Process the mesh in constant folder too.
            cm = RunUtility('transformPoints', '-allRegions', '-translate', f'({x} {y} {z})',
                            '-case', caseRoot, cwd=caseRoot)

            await cm.start()
            result = await cm.wait()

        return result

    @qasync.asyncSlot()
    async def rotate(self, origin, axis, angle):
        caseRoot = FileSystem.caseRoot()
        cm = RunParallelUtility('transformPoints', '-allRegions',
                                '-origin', f'({" ".join(origin)})',
                                '-rotate-angle', f'(({" ".join(axis)}) {angle})',
                                '-case', caseRoot, cwd=caseRoot, parallel=parallel.getEnvironment())
        await cm.start()
        result = await cm.wait()

        if result == 0 and parallel.getNP() > 1:  # Process the mesh in constant folder too.
            cm = RunUtility('transformPoints', '-allRegions',
                            '-origin', f'({" ".join(origin)})',
                            '-rotate-angle', f'(({" ".join(axis)}) {angle})',
                            '-case', caseRoot, cwd=caseRoot)

            await cm.start()
            result = await cm.wait()

        return result

    async def importMeshFiles(self, srcPath):
        path = self._checkAndCorrectMeshFolderSelection(srcPath)
        await self._copyMeshFrom(path)

    async def importPolyMeshes(self, polyMeshInfos):
        fluids = []
        solids = []

        for rname, path in polyMeshInfos:
            await asyncio.to_thread(
                shutil.copytree,
                path, FileSystem.constantPath(rname) / Directory.POLY_MESH_DIRECTORY_NAME, copy_function=shutil.copyfile)
            # if phase == Phase.SOLID:
            #     solids.append(rname)
            # else:
            #     fluids.append(rname)
            fluids.append(rname)

        RegionProperties().setRegions(fluids, solids).write()

    async def convertMesh(self, path, meshType):
        fileName = 'meshToConvert' + path.suffix
        await FileSystem.copyFileToCase(path, fileName)

        self._process = RunUtility(*OPENFOAM_MESH_CONVERTERS[meshType], fileName, cwd=FileSystem.caseRoot())
        await self._process.start()

        if await self._process.wait():
            await FileSystem.removeFile(fileName)
            raise RuntimeError(self.tr('File conversion failed.'))

        await FileSystem.removeFile(fileName)

    async def waitCellZonesInfo(self, path):
        fileName = 'meshToConvert' + path.suffix
        await FileSystem.copyFileToCase(path, fileName)

        self._process = FluentMeshConverter(fileName)

        return await self._process.waitCellZonesInfo()

    async def fulentCellZonesToRegions(self):
        return await self._process.cellZonesToRegions()

    def cancel(self):
        if self._process:
            self._process.cancel()

    @classmethod
    def convertUtility(cls, meshType):
        return OPENFOAM_MESH_CONVERTERS[meshType][0]

    async def _copyMeshFrom(self, source):
        await asyncio.to_thread(self._copyMeshFromInternal, source)

    def _copyMeshFromInternal(self, source):
        target = Project.instance().path / CASE_DIRECTORY_NAME / Directory.CONSTANT_DIRECTORY_NAME  # Constant Path for Live Case
        if target.exists():
            utils.rmtree(target)

        target.mkdir(exist_ok=True)

        regionPropFile = source / Directory.REGION_PROPERTIES_FILE_NAME
        if regionPropFile.is_file():
            shutil.copyfile(regionPropFile, target / Directory.REGION_PROPERTIES_FILE_NAME)
            regions = RegionProperties.loadRegions(source)
            for rname in regions:
                s = source / rname / Directory.POLY_MESH_DIRECTORY_NAME
                t = target / rname / Directory.POLY_MESH_DIRECTORY_NAME
                shutil.copytree(s, t, copy_function=shutil.copyfile)
        else:
            s = source / Directory.POLY_MESH_DIRECTORY_NAME
            t = target / Directory.POLY_MESH_DIRECTORY_NAME
            shutil.copytree(s, t, copy_function=shutil.copyfile)

    def _checkAndCorrectMeshFolderSelection(self, path: Path) -> Path:
        """Check if "path" has correct polyMesh

        Check if "path" has correct polyMesh
        "path" can point "polyMesh" or "constant" for single region mesh
        "path" should point "constant" for multi-region mesh

        Args:
            path: path for "constant" or "polyMesh"

        Returns:
            path for "constant" folder

        Raises:
            FileLoadingError: "path" does not have correct polyMesh
        """
        if isPolyMesh(path):
            return path.parent

        if isPolyMesh(path / 'polyMesh'):
            return path

        regionPropFile = path / Directory.REGION_PROPERTIES_FILE_NAME
        if not regionPropFile.is_file():
            raise FileLoadingError(f'PolyMesh not found.')

        regions = RegionProperties.loadRegions(path)
        for rname in regions:
            if not isPolyMesh(path / rname / 'polyMesh'):
                raise FileLoadingError(f'Corrupted Multi-Region PolyMesh')

        return path
