#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync
from PySide6.QtCore import QObject, Signal

from app import app
from openfoam.poly_mesh.poly_mesh_loader import PolyMeshLoader
from view.main_window.actor_manager import ActorGroup
from view.widgets.progress_dialog_simple import ProgressDialogSimple


class MeshManager(QObject):
    progress = Signal(str)

    def __init__(self, actorManager):
        super().__init__()
        self._actors = actorManager
        self._loaded = False

    async def load(self):
        self._actors.showGroup(ActorGroup.MESH)

        loader = PolyMeshLoader(app.fileSystem.foamFilePath())
        loader.progress.connect(self.progress)
        vtkMesh = await loader.loadMesh()

        if vtkMesh:
            for rname, region in vtkMesh.items():
                for bname, actorInfo in region['boundary'].items():
                    actorInfo.name = f'{region}:{bname}'
                    self._actors.add(actorInfo, ActorGroup.MESH)

            self._loaded = True

    def clear(self):
        self._actors.clearGroup(ActorGroup.MESH)

    @qasync.asyncSlot()
    async def showActors(self):
        self._actors.showGroup(ActorGroup.MESH)

        if not self._loaded:
            progressDialog = ProgressDialogSimple(app.window, self.tr('Loading Mesh'))
            progressDialog.setLabelText(self.tr('Loading Mesh'))
            progressDialog.open()

            self.progress.connect(progressDialog.setLabelText)
            await self.load()

            progressDialog.close()

    def hideActors(self):
        self._actors.hideGroup(ActorGroup.MESH)
