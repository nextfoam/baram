#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from app import app
from db.configurations_schema import CFDType, GeometryType, Shape
from db.simple_db import elementToVector
from openfoam.dictionary_file import DictionaryFile


def pointToEntry(point):
    x, y, z = point
    return f'({x} {y} {z})'


class CellSetSource:
    class Shape(Enum):
        HEX = 'hex'
        CYLINDER = 'cylinder'
        SPHERE = 'sphere'
        CELL_ZONE = 'cellZone'
        SURFACE = 'surface'

    def __init__(self, shape):
        self._shape = shape
        self._name = None

    @property
    def shape(self):
        return self._shape

    @property
    def name(self):
        return self._name

    def setName(self, name):
        self._name = name


class HexSource(CellSetSource):
    def __init__(self, minPoint, maxPoint):
        super().__init__(self.Shape.HEX)

        self._minPoint = minPoint
        self._maxPoint = maxPoint

    @property
    def minPoint(self):
        return self._minPoint

    @property
    def maxPoint(self):
        return self._maxPoint


class CylinderSource(CellSetSource):
    def __init__(self, axis1, axis2, radius):
        super().__init__(self.Shape.CYLINDER)

        self._axis1 = axis1
        self._axis2 = axis2
        self._radius = radius

    @property
    def axis1(self):
        return self._axis1

    @property
    def axis2(self):
        return self._axis2

    @property
    def radius(self):
        return self._radius


class SphereSource(CellSetSource):
    def __init__(self, centre, radius=1):
        super().__init__(self.Shape.SPHERE)

        self._centre = centre
        self._radius = radius

    @property
    def centre(self):
        return self._centre

    @property
    def radius(self):
        return self._radius


class TopoSetDict(DictionaryFile):
    def __init__(self, source=None):
        super().__init__(self.systemLocation(), 'topoSetDict')

        self._source = source

    def build(self):
        if self._data is not None:
            return self

        if self._source is None:    # Create cell zones
            actions = []
            for gId, geometry in app.db.getElements('geometry').items():
                if geometry['cfdType'] != CFDType.NONE.value and geometry['gType'] == GeometryType.VOLUME.value:
                    actions.append(self._constructClearCellSetAction(geometry['name']))
                    actions.append(self._constuctNewGeometryToCellAction(geometry))
                    actions.append(self._constructNewSetToCellZone(geometry['name'], geometry['name']))
        else:                       # Create cell sets for volume refinement
            actions = [
                self._constructClearCellSetAction(self._source.name),
                self._constructNewVolumeToCellAction(self._source)
            ]

        self._data = {
            'actions': actions
        }

        return self

    def _constructClearCellSetAction(self, name):
        return {
            'name': name,
            'type': 'cellSet',
            'action': 'clear'
        },

    def _constructNewVolumeToCellAction(self, source):
        if source.shape == CellSetSource.Shape.HEX:
            return self._constuctNewBoxToCellAction(source.name, source.minPoint, source.maxPoint)
        elif source.shape == CellSetSource.Shape.CYLINDER:
            return self._constsructNewCylinderToCellAction(source.name, source.axis1, source.axis2, source.radius)
        elif source.shape == CellSetSource.Shape.SPHERE:
            return self._constructNewSphereToCellAction(source.name, source.centre, source.radius)
        elif source.shape == CellSetSource.Shape.CELL_ZONE:
            return self._constructNewCellZoneToCellAction(source.name, None)

    def _constuctNewGeometryToCellAction(self, geometry):
        shape = geometry['shape']

        point1 = elementToVector(geometry['point1'])
        point2 = elementToVector(geometry['point2'])

        if shape == Shape.TRI_SURFACE_MESH.value:
            return self._constructNewSurfaceToCellAction(geometry['name'])
        elif shape == Shape.HEX.value:
            return self._constuctNewBoxToCellAction(geometry['name'], point1, point2)
        elif shape == Shape.CYLINDER.value:
            return self._constsructNewCylinderToCellAction(geometry['name'], point1, point2, geometry['radius'])
        elif shape == Shape.SPHERE.value:
            return self._constructNewSphereToCellAction(geometry['name'], point1, geometry['radius'])

    def _constructNewSetToCellZone(self, zoneName, setName):
        return {
            'name': zoneName,
            'type': 'cellZoneSet',
            'action': 'new',
            'source': 'setToCellZone',
            'sourceInfo': {
                'set': setName
            }
        }
    def _constuctNewBoxToCellAction(self, name, minPoint, maxPoint):
        data = self._createNewCellActionBase(name)
        data['source'] = 'boxToCell',
        data['box'] = (pointToEntry(minPoint), pointToEntry(maxPoint))

        return data

    def _constsructNewCylinderToCellAction(self, name, axis1, axis2, radius):
        data = self._createNewCellActionBase(name)
        data['source'] = 'cylinderToCell',
        data['p1'] = pointToEntry(axis1)
        data['p2'] = pointToEntry(axis2)
        data['radius'] = radius

        return data

    def _constructNewSphereToCellAction(self, name, centre, radius):
        data = self._createNewCellActionBase(name)
        data['source'] = 'sphereToCell'
        data['centre'] = pointToEntry(centre)
        data['radius'] = radius

        return data

    def _constructNewCellZoneToCellAction(self, name, cellZone):
        data = self._createNewCellActionBase(name)

        return data

    def _constructNewSurfaceToCellAction(self, name):
        data = self._createNewCellActionBase(name)
        data['source'] = 'surfaceToCell'
        data['file'] = f'constant/triSurface/{name}.stl'
        data['useSurfaceOrientation'] = 'true'
        data['includeInside'] = 'true'
        data['nearDistance'] = -1
        data['curvature'] = -100

        data['outsidePoints'] = []
        data['includeCut'] = 'false'
        data['includeOutside'] = 'false'

        return data

    def _createNewCellActionBase(self, name):
        return {
            'name': name,
            'type': 'cellSet',
            'action': 'new'
        }
