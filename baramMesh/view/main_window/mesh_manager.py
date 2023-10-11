#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Signal

from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.openfoam.poly_mesh.poly_mesh_loader import PolyMeshLoader
from baramMesh.rendering.actor_info import ActorInfo, ActorType
from baramMesh.view.main_window.actor_manager import ActorManager


class MeshManager(ActorManager):
    progress = Signal(str)

    def __init__(self):
        super().__init__()

        self._loader = None
        self._time = None

        self._name = 'Mesh'

    async def load(self, time=None):
        self.clear()
        self._visibility = True

        if time is not None:
            self._time = time

        if self._time is None:
            return

        progressDialog = ProgressDialog(app.window, self.tr('Loading Mesh'))
        progressDialog.setLabelText(self.tr('Loading Mesh'))
        progressDialog.open()

        self._loader = PolyMeshLoader(app.fileSystem.foamFilePath())
        self._loader.progress.connect(progressDialog.setLabelText)

        vtkMesh = await self._loader.loadMesh(self._time)
        if vtkMesh:
            for rname, region in vtkMesh.items():
                for bname, polyData in region['boundary'].items():
                    self.add(ActorInfo(polyData, bname, bname, ActorType.BOUNDARY))

            self.add(ActorInfo(vtkMesh['']['internalMesh'], 'internalMesh', 'internalMesh', ActorType.MESH))

        self.applyToDisplay()
        self.fitDisplay()

        progressDialog.close()

    def unload(self):
        self.hide()
        self._time = None

    @qasync.asyncSlot()
    async def show(self, time):
        if self._time == time:
            self._show()
        else:
            await self.load(time)

    def _connectSignalsSlots(self):
        self._loader.progress.connect(self.progress)
