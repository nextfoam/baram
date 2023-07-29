#!/usr/bin/env python
# -*- coding: utf-8 -*-

from vtkmodules.vtkFiltersCore import vtkFeatureEdges
from PySide6.QtCore import QObject, Signal

from app import app
from db.configurations_schema import GeometryType, Shape
from db.simple_db import elementToVector
from rendering.actor_info import ActorInfo
from view.main_window.actor_manager import ActorGroup
from rendering.vtk_loader import hexPolyData, sphereActor, cylinderActor, polygonPolyData, polyDataToActor


def polyDataToFeatureActor(polyData):
    edges = vtkFeatureEdges()
    edges.SetInputData(polyData)
    edges.Update()

    return polyDataToActor(edges.GetOutput())


def platePolyData(shape, volume):
    x1, y1, z1 = elementToVector(volume['point1'])
    x2, y2, z2 = elementToVector(volume['point2'])

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


class GeometryManager(QObject):
    listChanged = Signal()

    def __init__(self, actorManager):
        super().__init__()

        self._actors = actorManager
        self._geometries = {}
        self._volumes = {}
        self._bounds = None

    def geometries(self):
        return self._geometries

    def geometry(self, gId):
        return self._geometries[gId]

    def isEmpty(self):
        return not self._geometries

    def subSurfaces(self, gId):
        return self._volumes[gId]

    def load(self, visible):
        geometries = app.db.getElements('geometry', lambda i, e: e['volume'] == '')
        for gId, geometry in geometries.items():
            self.add(gId, geometry, visible)

        geometries = app.db.getElements('geometry', lambda i, e: e['volume'])
        for gId, geometry in geometries.items():
            self.add(gId, geometry, visible)

        self._visibie = visible

    def add(self, gId, geometry, visible=True):
        if geometry['gType'] == GeometryType.SURFACE.value:
            if geometry['volume']:

                self._volumes[geometry['volume']].append(gId)
            actorInfo = self._createActorInfo(geometry)
            actorInfo.name = gId
            actorInfo.setVisible(visible)

            if self._actors.isEmpty(ActorGroup.GEOMETRY):
                self._bounds = actorInfo.bounds()
            else:
                self._bounds.merge(actorInfo.bounds())
            self._actors.add(actorInfo, ActorGroup.GEOMETRY)
        else:
            self._volumes[gId] = []

        geometry['gId'] = gId
        self._geometries[gId] = geometry
        self.listChanged.emit()

    def update(self, gId, geometry, surfaces=None):
        geometry['gId'] = gId
        self._geometries[gId] = geometry

        if surfaces and geometry['shape'] != Shape.TRI_SURFACE_MESH.value:
            for gId in surfaces:
                self._actors.replace(self._createActorInfo(self._geometries[gId]), gId, ActorGroup.GEOMETRY)
            self._updateBounds()

    def remove(self, geometries):
        for gId, geometry in geometries.items():
            geometry = self._geometries.pop(gId)
            if geometry['gType'] == GeometryType.SURFACE.value:
                self._actors.remove(gId, ActorGroup.GEOMETRY)

        self._updateBounds()
        self.listChanged.emit()

    def showActor(self, gId):
        self._actors.show(gId, ActorGroup.GEOMETRY)

    def hideActor(self, gId):
        self._actors.hide(gId, ActorGroup.GEOMETRY)

    def showAll(self):
        self._actors.showAll(ActorGroup.GEOMETRY)

    def showActors(self):
        self._actors.showGroup(ActorGroup.GEOMETRY)

    def hideActors(self):
        self._actors.hideGroup(ActorGroup.GEOMETRY)

    def getBounds(self):
        return self._bounds

    def _createActorInfo(self, surface):
        shape = surface['shape']

        if shape == Shape.TRI_SURFACE_MESH.value:
            polyData = app.db.geometryPolyData(surface['path'])
            actorInfo = ActorInfo(polyDataToActor(polyData), polyDataToFeatureActor(polyData))
        else:
            volume = self._geometries[surface['volume']]
            if shape == Shape.HEX.value:
                polyData = hexPolyData(elementToVector(volume['point1']), elementToVector(volume['point2']))
                actorInfo = ActorInfo(polyDataToActor(polyData), polyDataToFeatureActor(polyData))
            elif shape == Shape.CYLINDER.value:
                actorInfo = ActorInfo(cylinderActor(elementToVector(volume['point1']),
                                                    elementToVector(volume['point2']),
                                                    float(volume['radius'])))
            elif shape == Shape.SPHERE.value:
                actorInfo = ActorInfo(sphereActor(elementToVector(volume['point1']), float(volume['radius'])))
            else:
                polyData = platePolyData(shape, volume)
                actorInfo = ActorInfo(polyDataToActor(polyData), polyDataToFeatureActor(polyData))

        return actorInfo

    def _updateBounds(self):
        self._bounds = self._actors.getBounds(ActorGroup.GEOMETRY)

