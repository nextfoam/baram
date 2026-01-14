#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

import qasync

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox, QMenu
from PySide6.QtCore import Signal

from libbaram.run import OpenFOAMError

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType, Shape, GeometryType
from baramMesh.view.step_page import StepPage
from widgets.async_message_box import AsyncMessageBox
from .geometry import RESERVED_NAMES
from .geometry_add_dialog import GeometryAddDialog
from .geometry_import_dialog import ImportDialog
from .geometry_list import GeometryList
from .split_dialog import SplitDialog
from .stl_utility import StlImporter
from .surface_dialog import SurfaceDialog
from .volume_dialog import VolumeDialog


class ContextMenu(QMenu):
    editActionTriggered = Signal()
    removeActionTriggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._removeAction = QAction(self.tr('Remove'), self)

        editAction = QAction(self.tr('Edit/View'), self)

        self.addAction(editAction)
        self.addAction(self._removeAction)

        editAction.triggered.connect(self.editActionTriggered)
        self._removeAction.triggered.connect(self.removeActionTriggered)

    def enableEditActions(self):
        self._removeAction.setVisible(True)

    def disableEditActions(self):
        self._removeAction.setVisible(False)


class GeometryPage(StepPage):
    geometryRemoved = Signal()

    def __init__(self, ui):
        super().__init__(ui, ui.geometryPage)

        self._geometryManager = None
        self._list = GeometryList(self._ui.geometryList)
        self._menu = None

        self._dialog = None
        self._menu = ContextMenu()
        self._actorsBackup = []

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        return app.db.elementCount('geometry') > 0

    async def show(self, isCurrentStep, batchRunning):
        if not self._loaded:
            self.load()

        app.window.meshManager.unload()

    def load(self):
        self._geometryManager = app.window.geometryManager
        self._list.load()

        self._geometryManager.selectedActorsChanged.connect(self._setSelectedGeometries)

        self._loaded = True

    async def hide(self):
        self._geometryManager.disableSyncingToDisplay()
        self._list.clearSelection()
        self._geometryManager.enableSyncingToDisplay()

        return True

    def retranslate(self):
        self._list.retranslate()

    def _connectSignalsSlots(self):
        self._ui.geometryList.customContextMenuRequested.connect(self._executeContextMenu)
        self._list.selectedItemsChanged.connect(self._selectedItemsChanged)
        self._ui.import_.clicked.connect(self._importClicked)
        self._ui.add.clicked.connect(self._addClicked)
        self._menu.editActionTriggered.connect(self._openEditDialog)
        self._menu.removeActionTriggered.connect(self._removeGeometry)

    def _executeContextMenu(self, pos):
        if self._locked:
            self._menu.disableEditActions()
        else:
            self._menu.enableEditActions()

        self._menu.exec(self._ui.geometryList.mapToGlobal(pos))

    def _selectedItemsChanged(self):
        self._geometryManager.selectActors(self._list.selectedIDs())

    @qasync.asyncSlot()
    async def _importClicked(self):
        self._dialog = ImportDialog(self._widget)
        self._dialog.accepted.connect(self._importSTL)
        self._dialog.open()

    def _addClicked(self):
        self._dialog = GeometryAddDialog(self._widget)
        self._dialog.shapeSelected.connect(self._openAddDialog)
        self._dialog.open()

    def _openAddDialog(self, shape):
        def addVolume():
            self._addVolume(self._dialog.gId())

        self._dialog = self._newVolumeDialog()
        self._dialog.setupForAdding(shape)
        self._dialog.accepted.connect(addVolume)
        self._dialog.open()

    def _openEditDialog(self):
        def updateVolume():
            gId = self._dialog.gId()
            volume = app.db.getElement('geometry',  gId)
            self._list.update(gId, volume)
            self._geometryManager.updateCustomSurfaces(volume, self._list.childSurfaces(gId))

        def updateSurfaces():
            gIds = self._dialog.gIds()
            for gId, surface in app.db.getElements('geometry', lambda i, e: i in gIds).items():
                self._list.update(gId, surface)
                self._geometryManager.updateIndependentSurface(gId, surface)

        items = self._list.selectedItems()

        sources = {}
        if len(items) == 1 and items[0].isVolume():
            gId = str(items[0].gId())
            for sId in self._list.childSurfaces(gId):
                actorInfo = self._geometryManager.actorInfo(sId)
                self._backupActor(actorInfo)
                sources[sId] = actorInfo.dataSet()

            self._dialog = self._newVolumeDialog()
            self._dialog.setupForEdit(gId, sources)
            self._dialog.accepted.connect(updateVolume)
            self._dialog.open()
        else:
            if len(items) == 1 and items[0].parent() is None:
                gId = str(items[0].gId())
                actorInfo = self._geometryManager.actorInfo(gId)
                self._backupActor(actorInfo)
                sources[gId] = actorInfo.dataSet()

            self._dialog = SurfaceDialog(self._widget, self._ui.renderingView)
            if not self._ui.geometryButtons.isEnabled():
                self._dialog.disableEdit()

            self._dialog.setData([item.gId() for item in items], sources)
            self._dialog.finished.connect(self._restoreActors)
            self._dialog.accepted.connect(updateSurfaces)
            self._dialog.open()

    @qasync.asyncSlot()
    async def _removeGeometry(self):
        if not await AsyncMessageBox().confirm(self._widget, self.tr("Remove Geometries"),
                                               self.tr('Are you sure you want to remove the selected items?')):
            return

        items = self._list.selectedItems()

        volume = None
        if len(items) == 1 and items[0].isVolume():
            volume = str(items[0].gId())
            surfaces = self._list.childSurfaces(volume)
        elif not any([item.geometry().value('volume') for item in items]):
            surfaces = {item.gId(): item.geometry() for item in items}
        else:
            await AsyncMessageBox().information(self._widget, self.tr('Delete Surfaces'),
                                                self.tr('Surfaces contained in a volume cannot be deleted.'))
            return

        db = app.db.checkout()

        for gId, surface in surfaces.items():
            db.removeGeometryPolyData(surface.value('path'))
            db.removeElement('geometry', gId)
            self._list.remove(gId)
        self._geometryManager.removeGeometry(surfaces)

        if volume:
            db.removeElement('geometry', volume)
            self._list.remove(volume)
            self._geometryManager.removeGeometry([volume])

        app.db.commit(db)

        self._updateNextStepAvailable()

        self.geometryRemoved.emit()

    @qasync.asyncSlot()
    async def _importSTL(self):
        def getUniqueSeq(name, seq):
            if seq == '' and name in RESERVED_NAMES:
                seq = 1

            return db.getUniqueSeq('geometry', 'name', name, seq)

        if self._dialog.featureAngle():
            splitDialog = SplitDialog(self._widget, self._dialog.files(), float(self._dialog.featureAngle()))
            try:
                volumes, surfaces = await splitDialog.show()
            except asyncio.exceptions.CancelledError:
                return
        else:
            stlImporter = StlImporter()
            stlImporter.load(self._dialog.files())
            volumes, surfaces = stlImporter.identifyVolumes()

        try:
            addedVolumes = []
            addedSurfaces = []

            db = app.db.checkout()
            seq = ''
            for volume in volumes:
                name = volume[0].sName if volume[0].sName else volume[0].fName
                seq = getUniqueSeq(name, seq)
                volumeName = name + seq
                element = db.newElement('geometry')
                element.setValue('gType', GeometryType.VOLUME)
                element.setValue('name', volumeName)
                element.setValue('shape', Shape.TRI_SURFACE_MESH.value)
                element.setValue('cfdType', CFDType.NONE.value)
                volumeId = db.addElement('geometry', element)
                addedVolumes.append(volumeId)

                sName = f'{volumeName}_surface'
                sseq = ''
                for surface in volume:
                    name = surface.sName if surface.sName and surface.sName != volumeName else sName
                    sseq = db.getUniqueSeq('geometry', 'name', name, sseq)
                    surfaceName = name + getUniqueSeq(name, sseq)
                    element = db.newElement('geometry')
                    element.setValue('gType', GeometryType.SURFACE.value)
                    element.setValue('volume', volumeId)
                    element.setValue('name', surfaceName)
                    element.setValue('shape', Shape.TRI_SURFACE_MESH.value)
                    element.setValue('cfdType', CFDType.BOUNDARY.value)
                    element.setValue('path', db.addGeometryPolyData(surface.polyData))
                    db.addElement('geometry', element)

            for surface in surfaces:
                name = surface.sName if surface.sName else surface.fName
                seq = getUniqueSeq(name, seq)
                surfaceName = name + seq
                element = db.newElement('geometry')
                element.setValue('gType', GeometryType.SURFACE.value)
                element.setValue('name', surfaceName)
                element.setValue('shape', Shape.TRI_SURFACE_MESH.value)
                element.setValue('cfdType', CFDType.BOUNDARY.value)
                element.setValue('path', db.addGeometryPolyData(surface.polyData))
                gId = db.addElement('geometry', element)
                addedSurfaces.append(gId)

            app.db.commit(db)

            for gId in addedVolumes:
                self._addVolume(gId)

            for gId in addedSurfaces:
                self._addSurface(gId)
        except OpenFOAMError as ex:
            code, message = ex.args
            QMessageBox.information(self._widget, self.tr('STL Loading Error'), f'{message} [{code}]')

    def _addVolume(self, gId):
        volume = app.db.getElement('geometry',  gId)
        self._addGeometry(gId, volume)

        surfaces = app.db.getElements('geometry', lambda i, e: e['volume'] == gId)
        for surfaceId in surfaces:
            self._addGeometry(surfaceId, surfaces[surfaceId], volume)

    def _addSurface(self, gId):
        surface = app.db.getElement('geometry',  gId)
        self._addGeometry(gId, surface, surface.value('volume'))

    def _addGeometry(self, gId, geometry, volume=None):
        self._geometryManager.addGeometry(gId, geometry, volume)
        self._list.add(gId, geometry)
        self._updateNextStepAvailable()

    def _setSelectedGeometries(self, gIds):
        if not self._locked:
            self._list.setSelectedItems(gIds)

        self._geometryManager.clearSyncingFromDisplay()

    def _enableStep(self):
        if self._geometryManager is not None:
            self._geometryManager.startSyncingFromDisplay()

        # self._ui.geometryList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._ui.geometryButtons.setEnabled(True)

    def _disableStep(self):
        # self._ui.geometryList.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._ui.geometryButtons.setEnabled(False)

    def _clear(self):
        self._list.clear()

    def _newVolumeDialog(self):
        dialog = VolumeDialog(self._widget, self._ui.renderingView)
        if not self._ui.geometryButtons.isEnabled():
            dialog.disableEdit()

        dialog.finished.connect(self._restoreActors)

        return dialog

    def _backupActor(self, actorInfo):
        self._actorsBackup.append((actorInfo, actorInfo.properties().opacity))
        actorInfo.setOpacity(0.1)

    def _restoreActors(self):
        for actorInfo, opacity in self._actorsBackup:
            actorInfo.setOpacity(opacity)

        self._actorsBackup.clear()
