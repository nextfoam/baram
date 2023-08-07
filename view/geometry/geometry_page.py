#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QMessageBox

from app import app
from db.configurations_schema import CFDType, Shape, GeometryType
from openfoam.run import OpenFOAMError
from view.step_page import StepPage
from .geometry_add_dialog import GeometryAddDialog
from .stl_file_loader import STLFileLoader
from .geometry_import_dialog import ImportDialog
from .volume_dialog import VolumeDialog
from .surface_dialog import SurfaceDialog
from .geometry_list import GeometryList


class GeometryPage(StepPage):
    def __init__(self, ui):
        super().__init__(ui, ui.geometryPage)

        self._geometries = None
        self._list = None
        self._loaded = False

        self._dialog = None
        self._geometryDialog = None

    def isNextStepAvailable(self):
        return not app.window.geometryManager.isEmpty()

    def lock(self):
        self._ui.buttons.setEnabled(False)

    def unlock(self):
        self._ui.buttons.setEnabled(True)

    def selected(self):
        if not self._loaded:
            self._geometries = app.window.geometryManager
            self._list = GeometryList(self._ui.geometryList, self._geometries)

            self._connectSignalsSlots()

            self._loaded = True

        app.window.geometryManager.showActors()
        app.window.meshManager.hideActors()

    def _connectSignalsSlots(self):
        self._geometries.listChanged.connect(self._updateNextStepAvailable)
        self._list.eyeToggled.connect(self._setGeometryVisibliity)
        self._list.itemDoubleClicked.connect(self._openEditDialog)
        self._ui.geometryList.currentItemChanged.connect(self._currentGeometryChanged)

        self._ui.import_.clicked.connect(self._importClicked)
        self._ui.add.clicked.connect(self._addClicked)
        self._ui.edit.clicked.connect(self._openEditDialog)
        self._ui.remove.clicked.connect(self._removeGeometry)

    @qasync.asyncSlot()
    async def _importClicked(self):
        self._dialog = ImportDialog(self._widget)
        self._dialog.accepted.connect(self._importSTL)
        self._dialog.open()

    def _addClicked(self):
        self._dialog = GeometryAddDialog(self._widget)
        self._dialog.accepted.connect(self._openAddDialog)
        self._dialog.open()

    def _openAddDialog(self):
        self._geometryDialog = VolumeDialog(self._widget)
        self._geometryDialog.setupForAdding(*self._dialog.geometryInfo())
        self._geometryDialog.accepted.connect(self._geometryAddAccepted)
        self._geometryDialog.open()

    def _editClicked(self):
        self._openEditDialog(self._list.currentGeometryID())

    def _openEditDialog(self, gId):
        geometry = self._geometries.geometry(gId)
        if geometry['gType'] == GeometryType.VOLUME.value:
            self._geometryDialog = VolumeDialog(self._widget)
            self._geometryDialog.setupForEdit(gId)
            self._geometryDialog.accepted.connect(self._updateVolume)
            self._geometryDialog.open()
        else:
            self._geometryDialog = SurfaceDialog(self._widget, gId)
            self._geometryDialog.accepted.connect(self._updateSurface)
            self._geometryDialog.open()

    def _removeGeometry(self):
        gId = self._list.currentGeometryID()

        db = app.db.checkout()
        geometries = db.getElements('geometry', lambda i, e: i == gId or e['volume'] == str(gId), ['path'])
        self._geometries.remove(geometries)

        for g in geometries:
            db.removeGeometryPolyData(geometries[g]['path'])
            db.removeElement('geometry', g)

        app.db.commit(db)

        self._list.remove(gId)

    def _updateNextStepAvailable(self):
        self._setNextStepEnabled(self.isNextStepAvailable())

    def _setGeometryVisibliity(self, gId, state):
        if state:
            self._geometries.showActor(gId)
        else:
            self._geometries.hideActor(gId)

    def _currentGeometryChanged(self):
        gId = self._list.currentGeometryID()
        if gId:
            geometry = self._geometries.geometry(gId)
            self._ui.edit.setEnabled(True)
            self._ui.remove.setEnabled(not geometry['volume'])

    @qasync.asyncSlot()
    async def _importSTL(self):
        try:
            path = self._dialog.filePath()

            loader = STLFileLoader()
            volumes, surfaces = await loader.load(path, self._dialog.featureAngle())

            added = []

            db = app.db.checkout()
            name = path.stem
            seq = ''
            for volume in volumes:
                seq = db.getUniqueSeq('geometry', 'name', name, seq)
                volumeName = f'{name}{seq}'
                element = db.newElement('geometry')
                element.setValue('gType', GeometryType.VOLUME)
                element.setValue('name', volumeName)
                element.setValue('shape', Shape.TRI_SURFACE_MESH.value)
                element.setValue('cfdType', CFDType.NONE.value)
                volumeId = db.addElement('geometry', element)
                added.append(volumeId)

                surfaceName = f'{volumeName}_surface_'
                sseq = '0'
                for polyData in volume:
                    sseq = db.getUniqueSeq('geometry', 'name', surfaceName, sseq)
                    element = db.newElement('geometry')
                    element.setValue('gType', GeometryType.SURFACE.value)
                    element.setValue('volume', volumeId)
                    element.setValue('name', f'{surfaceName}{sseq}')
                    element.setValue('shape', Shape.TRI_SURFACE_MESH.value)
                    element.setValue('cfdType', CFDType.NONE.value)
                    element.setValue('path', db.addGeometryPolyData(polyData))
                    db.addElement('geometry', element)

            for polyData in surfaces:
                seq = db.getUniqueSeq('geometry', 'name', name, seq)
                element = db.newElement('geometry')
                element.setValue('gType', GeometryType.SURFACE.value)
                element.setValue('name', f'{name}{seq}')
                element.setValue('shape', Shape.TRI_SURFACE_MESH.value)
                element.setValue('cfdType', CFDType.NONE.value)
                element.setValue('path', db.addGeometryPolyData(polyData))
                gId = db.addElement('geometry', element)
                added.append(gId)

            app.db.commit(db)

            for gId in added:
                self._geometryCreated(gId)
        except OpenFOAMError as ex:
            code, message = ex.args
            QMessageBox.information(self._widget, self.tr('STL Loading Error'), f'{message} [{code}]')

    def _geometryAddAccepted(self):
        self._geometryCreated(self._geometryDialog.gId())

    def _updateVolume(self):
        gId = self._geometryDialog.gId()
        geometry = app.db.getElement('geometry',  gId)
        self._geometries.update(gId, geometry, self._list.childSurfaces(gId))
        self._list.update(gId, geometry)

    def _updateSurface(self):
        gId = self._geometryDialog.gId()
        geometry = app.db.getElement('geometry',  gId)
        self._geometries.update(gId, geometry)
        self._list.update(gId, geometry)

    def _geometryCreated(self, gId):
        geometry = app.db.getElement('geometry',  gId)
        self._addGeometry(gId, geometry)

        if geometry['gType'] == GeometryType.VOLUME.value:
            surfaces = app.db.getElements('geometry', lambda i, e: e['volume'] == gId)
            for surfaceId in surfaces:
                self._addGeometry(surfaceId, surfaces[surfaceId])

    def _addGeometry(self, gId, geometry):
        self._geometries.add(gId, geometry)
        self._list.add(gId, geometry)
