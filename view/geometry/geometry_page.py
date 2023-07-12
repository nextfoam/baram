#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QWidget

from app import app
from db.configurations_schema import CFDType, Shape, GeometryType
from db.simple_db import elementToVector
from rendering.vtk_loader import hexActor, cylinderActor, sphereActor, polygonActor, polyDataToActor
from .geometry_add_dialog import GeometryAddDialog
from .stl_file_loader import STLFileLoader
from .geometry_import_dialog import ImportDialog
from .volume_dialog import VolumeDialog
from .surface_dialog import SurfaceDialog
from .geometry_list import GeometryList
from .geometry_page_ui import Ui_GeometryPage


class GeometryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_GeometryPage()
        self._ui.setupUi(self)

        self._list = GeometryList(self._ui.list)

        self._actors = app.window.actorManager()

        self._dialog = None
        self._geometryDialog = None

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._list.eyeToggled.connect(self._setGeometryVisibliity)
        self._ui.list.currentItemChanged.connect(self._currentGeometryChanged)

        self._ui.import_.clicked.connect(self._importClicked)
        self._ui.add.clicked.connect(self._addClicked)
        self._ui.edit.clicked.connect(self._openEditDialog)
        self._ui.remove.clicked.connect(self._removeGeometry)

    @qasync.asyncSlot()
    async def _importClicked(self):
        self._dialog = ImportDialog(self)
        self._dialog.accepted.connect(self._importSTL)
        self._dialog.open()

    def _addClicked(self):
        self._dialog = GeometryAddDialog(self)
        self._dialog.accepted.connect(self._openAddDialog)
        self._dialog.open()

    def _openAddDialog(self):
        self._geometryDialog = VolumeDialog(self)
        self._geometryDialog.setupForAdding(*self._dialog.geometryInfo())
        self._geometryDialog.accepted.connect(self._geometryAddAccepted)
        self._geometryDialog.open()

    def _openEditDialog(self):
        geometry = self._list.currentGeometry()
        if geometry['gType'] == GeometryType.VOLUME.value:
            self._geometryDialog = VolumeDialog(self)
            self._geometryDialog.setupForEdit(self._list.currentGeometryID())
            self._geometryDialog.accepted.connect(self._updateVolume)
            self._geometryDialog.open()
        else:
            self._geometryDialog = SurfaceDialog(self, self._list.currentGeometryID())
            self._geometryDialog.accepted.connect(self._updateSurface)
            self._geometryDialog.open()

    def _removeGeometry(self):
        gId = self._list.currentGeometryID()

        db = app.db.checkout()
        geometries = db.getElements('geometry', lambda i, e: i == gId or e['volume'] == str(gId), ['path'])

        for g in geometries:
            self._actors.remove(g)
            db.removeGeometryPolyData(geometries[g]['path'])
            db.removeElement('geometry', g)
        self._actors.refresh()

        app.db.commit(db)

        self._list.remove(gId)

    def _load(self):
        geometries = app.db.getElements('geometry', lambda i, e: e['volume'] == '')
        for gId in geometries:
            self._addGeometry(gId, geometries[gId])

        geometries = app.db.getElements('geometry', lambda i, e: e['volume'])
        for gId in geometries:
            self._addGeometry(gId, geometries[gId])

        self._actors.fitCamera()

    def _setGeometryVisibliity(self, gId, state):
        if state:
            self._actors.show(gId)
        else:
            self._actors.hide(gId)

    def _currentGeometryChanged(self):
        geometry = self._list.currentGeometry()

        self._ui.edit.setEnabled(geometry is not None)
        self._ui.remove.setEnabled(geometry is not None and not geometry['volume'])

    @qasync.asyncSlot()
    async def _importSTL(self):
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
        self._actors.refresh()

    def _geometryAddAccepted(self):
        self._geometryCreated(self._geometryDialog.gId())
        self._actors.refresh()

    def _updateVolume(self):
        gId = self._geometryDialog.gId()
        geometry = app.db.getElement('geometry',  gId)
        self._list.update(gId, geometry)

        if geometry['shape'] != Shape.TRI_SURFACE_MESH.value:
            for item in self._list.childSurfaces(gId):
                self._actors.replace(self._createActor(item.gId(), item.geometry()), str(item.gId()))

    def _updateSurface(self):
        gId = self._geometryDialog.gId()
        geometry = app.db.getElement('geometry',  gId)
        self._list.update(gId, geometry)

    def _geometryCreated(self, gId):
        geometry = app.db.getElement('geometry',  gId)
        self._addGeometry(gId, geometry)

        if geometry['gType'] == GeometryType.VOLUME.value:
            surfaces = app.db.getElements('geometry', lambda i, e: e['volume'] == gId)
            for surfaceId in surfaces:
                self._addGeometry(surfaceId, surfaces[surfaceId])

    def _addGeometry(self, gId, geometry):
        self._list.add(gId, geometry)

        if geometry['gType'] == GeometryType.SURFACE.value:
            self._actors.add(self._createActor(gId, geometry), gId)

    def _createActor(self, gId, surface):
        volume = self._list.geometry(surface['volume'])
        shape = surface['shape']

        actor = None
        if shape == Shape.TRI_SURFACE_MESH.value:
            actor = polyDataToActor(app.db.geometryPolyData(surface['path']))
        elif shape == Shape.HEX.value:
            actor = hexActor(elementToVector(volume['point1']), elementToVector(volume['point2']))
        elif shape == Shape.SPHERE.value:
            actor = sphereActor(elementToVector(volume['point1']), float(volume['radius']))
        elif shape == Shape.CYLINDER.value:
            actor = cylinderActor(
                elementToVector(volume['point1']), elementToVector(volume['point2']), float(volume['radius']))
        elif shape in Shape.PLATES.value:
            x1, y1, z1 = elementToVector(volume['point1'])
            x2, y2, z2 = elementToVector(volume['point2'])

            if shape == Shape.X_MIN.value:
                actor = polygonActor([(x1, y1, z1), (x1, y1, z2), (x1, y2, z2), (x1, y2, z1)])
            elif shape == Shape.X_MAX.value:
                actor = polygonActor([(x2, y1, z1), (x2, y1, z2), (x2, y2, z2), (x2, y2, z1)])
            elif shape == Shape.Y_MIN.value:
                actor = polygonActor([(x1, y1, z1), (x2, y1, z1), (x2, y1, z2), (x1, y1, z2)])
            elif shape == Shape.Y_MAX.value:
                actor = polygonActor([(x1, y2, z1), (x2, y2, z1), (x2, y2, z2), (x1, y2, z2)])
            elif shape == Shape.Z_MIN.value:
                actor = polygonActor([(x1, y1, z1), (x1, y2, z1), (x2, y2, z1), (x2, y1, z1)])
            elif shape == Shape.Z_MAX.value:
                actor = polygonActor([(x1, y1, z2), (x1, y2, z2), (x2, y2, z2), (x2, y1, z2)])

        actor.SetObjectName(gId)
        return actor
