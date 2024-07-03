#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal

from baramMesh.app import app
from baramMesh.db.configurations_schema import GeometryType, Shape
from baramMesh.rendering.actor_info import GeometryActor
from baramMesh.rendering.vtk_loader import hexPolyData, cylinderPolyData, spherePolyData, polygonPolyData
from baramMesh.view.main_window.actor_manager import ActorManager


def platePolyData(shape, volume):
    x1, y1, z1 = volume.vector('point1')
    x2, y2, z2 = volume.vector('point2')

    if shape == Shape.X_MIN.value:
        return polygonPolyData([(x1, y1, z1), (x1, y1, z2), (x1, y2, z2), (x1, y2, z1)])
    elif shape == Shape.X_MAX.value:
        return polygonPolyData([(x2, y1, z1), (x2, y1, z2), (x2, y2, z2), (x2, y2, z1)])
    elif shape == Shape.Y_MIN.value:
        return polygonPolyData([(x1, y1, z1), (x2, y1, z1), (x2, y1, z2), (x1, y1, z2)])
    elif shape == Shape.Y_MAX.value:
        return polygonPolyData([(x1, y2, z1), (x2, y2, z1), (x2, y2, z2), (x1, y2, z2)])
    elif shape == Shape.Z_MIN.value:
        return polygonPolyData([(x1, y1, z1), (x1, y2, z1), (x2, y2, z1), (x2, y1, z1)])
    elif shape == Shape.Z_MAX.value:
        return polygonPolyData([(x1, y1, z2), (x1, y2, z2), (x2, y2, z2), (x2, y1, z2)])


class GeometryManager(ActorManager):
    selectedActorsChanged = Signal(list)

    SYNCING_FROM_DISPLAY = 1
    SYNCING_TO_DISPLAY = 2

    def __init__(self):
        super().__init__()

        self._syncingMode = None

        self._displayController.selectedActorsChanged.connect(self._selectedActorsChanged)
        self._displayController.selectionApplied.connect(self._clearSyncingToDisplay)

    def subSurfaces(self, gId):
        return app.db.getElements('geometry', lambda i, e: e['volume'] == gId)

    def polyData(self, gId):
        return self._actorInfos[gId].dataSet()

    def load(self):
        self.clear()
        self._visibility = True

        geometries = app.db.getElements('geometry')
        for gId, geometry in geometries.items():
            self._add(gId, geometry, geometries.get(geometry.value('volume')))

        self.fitDisplay()

    def addGeometry(self, gId, geometry, volume):
        self._add(gId, geometry, volume)

        self.applyToDisplay()

    def updateVolume(self, geometry, surfaces=None):
        if surfaces and geometry.value('shape') != Shape.TRI_SURFACE_MESH.value:
            for gId, surface in surfaces.items():
                self.update(gId, self._surfaceToPolyData(surface, geometry))

        self.applyToDisplay()

    def updateSurface(self, gId, surface):
        self._updateActorName(gId, surface.value('name'))

    def removeGeometry(self, gIds):
        for gId in gIds:
            self.remove(gId)

        self.applyToDisplay()

    def show(self):
        self._show()

    def selectActors(self, ids):
        if self._syncingMode == self.SYNCING_FROM_DISPLAY:
            return

        self._syncingMode = self.SYNCING_TO_DISPLAY
        self._displayController.setSelectedActors(ids)

    def clearSyncingFromDisplay(self):
        if self._syncingMode != self.SYNCING_FROM_DISPLAY:
            raise RuntimeError

        self._syncingMode = None

    def startSyncingFromDisplay(self):
        self._displayController.selectedItemsChanged()

    def enableSyncingToDisplay(self):
        if self._syncingMode == self.SYNCING_TO_DISPLAY:
            return

        self._syncingMode = None

    def disableSyncingToDisplay(self):
        self._syncingMode = self.SYNCING_FROM_DISPLAY

    def getBoundingHex6(self):
        boundingHex6 = app.db.getValue('baseGrid/boundingHex6')  # can be "None"
        if boundingHex6 is None:
            return None, None

        geometry = app.db.getElement('geometry', boundingHex6)
        if (geometry is None
                or geometry.value('gType') != GeometryType.VOLUME.value
                or geometry.value('shape') != Shape.HEX6.value):
            return None, None

        return boundingHex6, geometry

    def isBoundingHex6(self, gId):
        if not app.db.hasElement('geometry', gId):
            return False

        boundingHex6 = app.db.getValue('baseGrid/boundingHex6')  # can be "None"

        geometry = app.db.getElement('geometry', gId)
        if geometry.value('gType') == GeometryType.VOLUME.value:
            if gId == boundingHex6:
                return True
        elif geometry.value('gType') == GeometryType.SURFACE.value:
            if geometry.value('shape') in Shape.PLATES.value and geometry.value('volume') == boundingHex6:
                return True

        return False

    def _add(self, gId, geometry, volume):
        if geometry.value('gType') == GeometryType.SURFACE.value:
            self.add(GeometryActor(self._surfaceToPolyData(geometry, volume), gId, geometry.value('name')))

    def _surfaceToPolyData(self, surface, volume):
        shape = surface.value('shape')

        if shape == Shape.TRI_SURFACE_MESH.value:
            polyData = app.db.geometryPolyData(surface.value('path'))
        else:
            if shape == Shape.HEX.value:
                polyData = hexPolyData(volume.vector('point1'), volume.vector('point2'))
            elif shape == Shape.CYLINDER.value:
                polyData = cylinderPolyData(volume.vector('point1'), volume.vector('point2'), volume.float('radius'))
            elif shape == Shape.SPHERE.value:
                polyData = spherePolyData(volume.vector('point1'), volume.float('radius'))
            else:  # Shape.HEX6.value
                polyData = platePolyData(shape, volume)

        return polyData

    def _selectedActorsChanged(self, gIds):
        if self._syncingMode == self.SYNCING_TO_DISPLAY:
            return

        self._syncingMode = self.SYNCING_FROM_DISPLAY
        self.selectedActorsChanged.emit(gIds)

    def _clearSyncingToDisplay(self):
        if self._syncingMode != self.SYNCING_TO_DISPLAY:
            raise RuntimeError

        self._syncingMode = None
