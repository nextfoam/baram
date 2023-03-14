#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import qasync

from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtCore import Signal

from openfoam.run import runUtility
from openfoam.file_system import FileSystem
from openfoam.polymesh.polymesh_loader import PolyMeshLoader
from view.widgets.progress_dialog_simple import ProgressDialogSimple


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


class MeshManager(QObject):
    meshChanged = Signal()

    def __init__(self, window):
        super().__init__()

        self._window = window

    @qasync.asyncSlot()
    async def scale(self, x, y, z):
        progressDialog = ProgressDialogSimple(self._window, self.tr('Mesh Scaling'))
        progressDialog.open()

        progressDialog.setLabelText(self.tr('Scaling the mesh.'))

        try:
            proc = await runUtility('transformPoints', '-allRegions', '-scale', f'({x} {y} {z})',
                                    cwd=FileSystem.caseRoot())
            result = await proc.wait()

            if result:
                progressDialog.finish(self.tr('Mesh scaling failed.'))
            else:
                progressDialog.finish(self.tr('Mesh scaling is complete'))
                self.meshChanged.emit()
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    @qasync.asyncSlot()
    async def translate(self, x, y, z):
        progressDialog = ProgressDialogSimple(self._window, self.tr('Mesh Translation'))
        progressDialog.open()

        progressDialog.setLabelText(self.tr('Translating the mesh.'))

        try:
            proc = await runUtility(
                'transformPoints', '-allRegions', '-translate', f'({x} {y} {z})', cwd=FileSystem.caseRoot())
            result = await proc.wait()

            if result:
                progressDialog.finish(self.tr('Mesh translation failed.'))
            else:
                progressDialog.finish(self.tr('Mesh translation is complete'))
                self.meshChanged.emit()
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    @qasync.asyncSlot()
    async def rotate(self, origin, axis, angle):
        progressDialog = ProgressDialogSimple(self._window, self.tr('Mesh Rotation'))
        progressDialog.open()

        progressDialog.setLabelText(self.tr('Rotating the mesh.'))

        try:
            proc = await runUtility('transformPoints', '-allRegions',
                                    '-origin', f'({" ".join(origin)})',
                                    '-rotate-angle', f'(({" ".join(axis)}) {angle})',
                                    cwd=FileSystem.caseRoot())
            result = await proc.wait()

            if result:
                progressDialog.finish(self.tr('Mesh rotation failed.'))
            else:
                progressDialog.finish(self.tr('Mesh rotation is complete'))
                self.meshChanged.emit()
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    async def importOpenFoamMesh(self, path: Path):
        progressDialog = ProgressDialogSimple(self._window, self.tr('Mesh Loading'))
        progressDialog.open()

        progressDialog.setLabelText(self.tr('Checking the mesh.'))

        try:
            progressDialog.setLabelText(self.tr('Loading the boundaries.'))
            await PolyMeshLoader().loadMesh(path)
            progressDialog.close()
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    async def importMesh(self, path, meshType):
        progressDialog = ProgressDialogSimple(self._window, self.tr('Mesh Loading'))
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
                await PolyMeshLoader().loadMesh()
                await FileSystem.removeFile(path.name)
                progressDialog.close()
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    @classmethod
    def convertUtility(cls, meshType):
        return OPENFOAM_MESH_CONVERTERS[meshType][0]
