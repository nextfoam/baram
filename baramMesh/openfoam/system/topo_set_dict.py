#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType, Shape


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
    class Mode(Enum):
        CREATE_REGIONS = 0
        CREATE_CELL_ZONES = 1

    def __init__(self):
        super().__init__(app.fileSystem.caseRoot(), self.systemLocation(), 'topoSetDict')

    def setRegion(self, rname):
        self._rname = rname
        self._header['location'] = str(self.systemLocation(rname))

        return self

    def build(self, mode):
        if self._data is not None:
            return self

        actions = []
        regions = app.db.getElements('region')
        if mode == self.Mode.CREATE_REGIONS:
            for region in regions.values():
                actions.append(self._constructClearCellSetAction(region.value('name')))
                actions.append(self._constuctNewRegionToCellAction(region))
                actions.append(self._constructNewSetToCellZone(region.value('name'), region.value('name')))
        elif mode == self.Mode.CREATE_CELL_ZONES:
            for gId, geometry in app.db.getElements(
                    'geometry', lambda i, e: e['cfdType'] == CFDType.CELL_ZONE.value).items():
                actions.append(self._constructClearCellSetAction(geometry.value('name')))
                actions.append(self._constuctNewGeometryToCellAction(geometry))
                actions.append(self._constructNewSetToCellZone(geometry.value('name'), geometry.value('name')))

            if len(regions) > 1:
                for region in regions.values():
                    actions.append(self._constructRemoveCellZoneSet(region.value('name')))

        if actions:
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

    def _constuctNewRegionToCellAction(self, region):
        return {
            'name': region.value('name'),
            'type': 'cellSet',
            'action': 'new',
            'source': 'regionToCell',
            'insidePoints': [region.vector('point')]
        }

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
        shape = geometry.value('shape')

        point1 = geometry.vector('point1')
        point2 = geometry.vector('point2')

        if shape == Shape.TRI_SURFACE_MESH.value:
            return self._constructNewSurfaceToCellAction(geometry.value('name'))
        elif shape == Shape.HEX.value or shape == Shape.HEX6.value:
            return self._constuctNewBoxToCellAction(geometry.value('name'), point1, point2)
        elif shape == Shape.CYLINDER.value:
            return self._constsructNewCylinderToCellAction(
                geometry.value('name'), point1, point2, geometry.value('radius'))
        elif shape == Shape.SPHERE.value:
            return self._constructNewSphereToCellAction(geometry.value('name'), point1, geometry.value('radius'))

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

    def _constructRemoveCellZoneSet(self, zoneName):
        return {
            'name': zoneName,
            'type': 'cellZoneSet',
            'action': 'remove',
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
