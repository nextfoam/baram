#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import app
from db.configurations_schema import GeometryType, Shape
from db.simple_db import elementToVector
from rendering.actor_info import ActorInfo, ActorType
from rendering.vtk_loader import hexPolyData, cylinderPolyData, spherePolyData, polygonPolyData
from view.main_window.actor_manager import ActorManager


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


class GeometryManager(ActorManager):
    def __init__(self):
        super().__init__()

        self._geometries = {}
        self._volumes = {}

        self._name = 'Geometry'

    def geometries(self):
        return self._geometries

    def geometry(self, gId):
        return self._geometries[gId]

    def subSurfaces(self, gId):
        return self._volumes[gId]

    def polyData(self, gId):
        return self._actorInfos[gId].polyData()

    def load(self):
        self.clear()
        self._visibility = True

        geometries = app.db.getElements('geometry', lambda i, e: e['volume'] is None)
        for gId, geometry in geometries.items():
            self._add(gId, geometry)

        geometries = app.db.getElements('geometry', lambda i, e: e['volume'])
        for gId, geometry in geometries.items():
            self._add(gId, geometry)

        self.fitDisplay()

    def addGeometry(self, gId, geometry):
        self._add(gId, geometry)

        self.applyToDisplay()

    def updateGeometry(self, gId, geometry, surfaces=None):
        geometry['gId'] = gId
        self._geometries[gId] = geometry

        if surfaces and geometry['shape'] != Shape.TRI_SURFACE_MESH.value:
            for gId in surfaces:
                self.update(
                    ActorInfo(self._surfaceToPolyData(self._geometries[gId]),
                              gId, geometry['name'], ActorType.GEOMETRY))
        else:
            self._updateActorName(gId, geometry['name'])

        self.applyToDisplay()

    def removeGeometry(self, geometries):
        for gId, geometry in geometries.items():
            geometry = self._geometries.pop(gId)
            if geometry['gType'] == GeometryType.SURFACE.value:
                self.remove(gId)

        self.applyToDisplay()

    def updateGeometryPropety(self, gId, name, value):
        self._geometries[gId][name] = value

    def show(self):
        self._show()

    def _add(self, gId, geometry):
        if geometry['gType'] == GeometryType.SURFACE.value:
            if geometry['volume']:
                self._volumes[geometry['volume']].append(gId)

            self.add(ActorInfo(self._surfaceToPolyData(geometry), gId, geometry['name'], ActorType.GEOMETRY))
        else:
            self._volumes[gId] = []

        geometry['gId'] = gId
        self._geometries[gId] = geometry

    def _surfaceToPolyData(self, surface):
        shape = surface['shape']

        if shape == Shape.TRI_SURFACE_MESH.value:
            polyData = app.db.geometryPolyData(surface['path'])
        else:
            volume = self._geometries[surface['volume']]
            if shape == Shape.HEX.value:
                polyData = hexPolyData(elementToVector(volume['point1']), elementToVector(volume['point2']))
            elif shape == Shape.CYLINDER.value:
                polyData = cylinderPolyData(elementToVector(volume['point1']),
                                            elementToVector(volume['point2']),
                                            float(volume['radius']))
            elif shape == Shape.SPHERE.value:
                polyData = spherePolyData(elementToVector(volume['point1']), float(volume['radius']))
            else:
                polyData = platePolyData(shape, volume)

        return polyData
