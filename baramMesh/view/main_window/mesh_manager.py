#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Signal

from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.openfoam.poly_mesh.poly_mesh_loader import PolyMeshLoader
from baramMesh.rendering.actor_info import ActorInfo, BoundaryActor, MeshActor, MeshQualityIndex
from baramMesh.view.main_window.actor_manager import ActorManager


class MeshManager(ActorManager):
    cellCountChanged = Signal(int)

    def __init__(self):
        super().__init__()

        self._loader = None
        self._time = None

        self._name = 'Mesh'

    async def load(self, time=None):
        if not self._displayControl.isEnabled():
            return

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
                    self.add(BoundaryActor(polyData, bname, bname))

            self.add(MeshActor(vtkMesh['']['internalMesh'], 'internalMesh', 'internalMesh'))

        self.applyToDisplay()
        self.fitDisplay()

        self._notifyCellCountChange()

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

    def boundaries(self):
        return self._actorInfos.keys()

    def getScalarRange(self, index: MeshQualityIndex) -> (float, float):
        actorInfo: ActorInfo
        for actorInfo in self._actorInfos.values():
            if isinstance(actorInfo, MeshActor):
                return actorInfo.getScalarRange(index)

    def getNumberOfDisplayedCells(self) -> int:
        actorInfo: ActorInfo
        for actorInfo in self._actorInfos.values():
            if isinstance(actorInfo, MeshActor):
                return actorInfo.getNumberOfDisplayedCells()

    def setScalar(self, index: MeshQualityIndex):
        for actorInfo in self._actorInfos.values():
            actorInfo.setScalar(index)

    def setScalarBand(self, low, high):
        for actorInfo in self._actorInfos.values():
            actorInfo.setScalarBand(low, high)

    def clearCellFilter(self):
        for actorInfo in self._actorInfos.values():
            actorInfo.clearCellFilter()

        self._notifyCellCountChange()

    def applyCellFilter(self):
        for actorInfo in self._actorInfos.values():
            actorInfo.applyCellFilter()

        self._notifyCellCountChange()

    def clip(self, planes):
        super().clip(planes)
        self._notifyCellCountChange()

    def slice(self, plane):
        super().slice(plane)
        self._notifyCellCountChange()

    def _notifyCellCountChange(self):
        count = self.getNumberOfDisplayedCells()
        self.cellCountChanged.emit(count)

    def _show(self):
        super()._show()
        self._notifyCellCountChange()
