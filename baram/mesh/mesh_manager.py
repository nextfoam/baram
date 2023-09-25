#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import qasync

from enum import Enum, auto
from pathlib import Path

from baram.openfoam.redistribution_task import RedistributionTask
from libbaram.run import runUtility, runParallelUtility
from widgets.progress_dialog import ProgressDialog

from baram.openfoam import parallel
from baram.openfoam.file_system import FileSystem
from baram.openfoam.polymesh.polymesh_loader import PolyMeshLoader
from libbaram.process import Processor


logger = logging.getLogger(__name__)


class MeshType(Enum):
    POLY_MESH = auto()
    FLUENT_2D = auto()
    FLUENT_3D = auto()
    STAR_CCM = auto()
    GMSH = auto()
    IDEAS = auto()
    NAMS_PLOT3D = auto()


OPENFOAM_MESH_CONVERTERS = {
    MeshType.POLY_MESH: None,
    MeshType.FLUENT_2D: ('fluentMeshToFoam', '-writeSets', '-writeZones'),
    MeshType.FLUENT_3D: ('fluent3DMeshToFoam',),
    MeshType.STAR_CCM: ('ccm26ToFoam',),
    MeshType.GMSH: ('gmshToFoam',),
    MeshType.IDEAS: ('ideasUnvToFoam',),
    MeshType.NAMS_PLOT3D: ('plot3dToFoam',),
}


class MeshManager(Processor):
    def __init__(self, window):
        super().__init__()

        self._window = window

    @qasync.asyncSlot()
    async def scale(self, x, y, z):
        caseRoot = FileSystem.caseRoot()
        self._proc = await runParallelUtility('transformPoints', '-allRegions', '-scale', f'({x} {y} {z})',
                                              '-case', caseRoot, parallel=parallel.getEnvironment(), cwd=caseRoot)
        return await self._proc.wait()

    @qasync.asyncSlot()
    async def translate(self, x, y, z):
        caseRoot = FileSystem.caseRoot()
        self._proc = await runParallelUtility('transformPoints', '-allRegions', '-translate', f'({x} {y} {z})',
                                              '-case', caseRoot, parallel=parallel.getEnvironment(), cwd=caseRoot)
        return await self._proc.wait()

    @qasync.asyncSlot()
    async def rotate(self, origin, axis, angle):
        caseRoot = FileSystem.caseRoot()
        self._proc = await runParallelUtility('transformPoints', '-allRegions',
                                              '-origin', f'({" ".join(origin)})',
                                              '-rotate-angle', f'(({" ".join(axis)}) {angle})',
                                              '-case', caseRoot, parallel=parallel.getEnvironment(), cwd=caseRoot)
        return await self._proc.wait()

    async def importOpenFoamMesh(self, path: Path):
        progressDialog = ProgressDialog(self._window, self.tr('Mesh Loading'))
        progressDialog.open()

        progressDialog.setLabelText(self.tr('Checking the mesh.'))

        try:
            progressDialog.setLabelText(self.tr('Loading the boundaries.'))
            # Need to load mesh to get region information though redistribution loads mesh in next lines
            await PolyMeshLoader().loadMesh(path)

            redistributeTask = RedistributionTask()
            redistributeTask.progress.connect(progressDialog.setLabelText)
            await redistributeTask.redistribute()

            progressDialog.close()
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    async def importMesh(self, path, meshType):
        progressDialog = ProgressDialog(self._window, self.tr('Mesh Loading'))
        progressDialog.open()

        progressDialog.setLabelText(self.tr('Converting the mesh.'))

        try:
            await FileSystem.copyFileToCase(path)

            proc = await runUtility(*OPENFOAM_MESH_CONVERTERS[meshType], path.name, cwd=FileSystem.caseRoot())

            progressDialog.showCancelButton()
            progressDialog.cancelClicked.connect(proc.terminate)

            if await proc.wait():
                progressDialog.finish(self.tr('File conversion failed.'))
            elif not progressDialog.isCanceled():
                progressDialog.setLabelText(self.tr('Loading the boundaries.'))
                # Need to load mesh to get region information though redistribution loads mesh in next lines
                await PolyMeshLoader().loadMesh()
                await FileSystem.removeFile(path.name)

                redistributeTask = RedistributionTask()
                redistributeTask.progress.connect(progressDialog.setLabelText)
                await redistributeTask.redistribute()

                progressDialog.close()
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    @classmethod
    def convertUtility(cls, meshType):
        return OPENFOAM_MESH_CONVERTERS[meshType][0]
