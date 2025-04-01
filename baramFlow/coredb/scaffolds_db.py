#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from uuid import UUID, uuid4

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_scaffold import BoundaryScaffold
from baramFlow.coredb.disk_scaffold import DiskScaffold
from baramFlow.coredb.iso_surface import IsoSurface
from baramFlow.coredb.libdb import nsmap

from baramFlow.coredb.line_scaffold import LineScaffold
from baramFlow.coredb.parallelogram import Parallelogram
from baramFlow.coredb.scaffold import Scaffold
from baramFlow.coredb.sphere_scaffold import SphereScaffold
from libbaram.async_signal import AsyncSignal


BOUNDARY_SCAFFOLD_NAME_PREFIX = 'boundary'
ISO_SURFACE_NAME_PREFIX = 'iso-surface'
DISK_SCAFFOLD_NAME_PREFIX = 'disk-scaffold'
LINE_SCAFFOLD_NAME_PREFIX = 'line-scaffold'
PARALLELOGRAM_NAME_PREFIX = 'parallelogram'
SPHERE_SCAFFOLD_NAME_PREFIX = 'sphere-scaffold'

_mutex = Lock()


class ScaffoldsDB:
    SCAFFOLDS_PATH = '/scaffolds'

    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(ScaffoldsDB, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        with _mutex:
            if hasattr(self, '_initialized'):
                return
            else:
                self._initialized = True

        self.scaffoldAdded = AsyncSignal(UUID)
        self.scaffoldUpdated = AsyncSignal(UUID)
        self.removingScaffold = AsyncSignal(UUID)

        self._scaffolds: dict[UUID, Scaffold] = {}

    def load(self):
        self._scaffolds = self._parseScaffolds()

    def _parseScaffolds(self) -> dict[UUID, Scaffold]:
        scaffolds = {}
        root = coredb.CoreDB().getElement(self.SCAFFOLDS_PATH)

        parent = root.find('boundaries', namespaces=nsmap)
        for e in parent.findall('boundary', namespaces=nsmap):
            s = BoundaryScaffold.fromElement(e)
            scaffolds[s.uuid] = s
            s.instanceUpdated.asyncConnect(self._scaffoldUpdated)

        parent = root.find('isoSurfaces', namespaces=nsmap)
        for e in parent.findall('surface', namespaces=nsmap):
            s = IsoSurface.fromElement(e)
            scaffolds[s.uuid] = s
            s.instanceUpdated.asyncConnect(self._scaffoldUpdated)

        parent = root.find('diskScaffolds', namespaces=nsmap)
        for e in parent.findall('diskScaffold', namespaces=nsmap):
            s = DiskScaffold.fromElement(e)
            scaffolds[s.uuid] = s
            s.instanceUpdated.asyncConnect(self._scaffoldUpdated)

        parent = root.find('lineScaffolds', namespaces=nsmap)
        for e in parent.findall('lineScaffold', namespaces=nsmap):
            s = LineScaffold.fromElement(e)
            scaffolds[s.uuid] = s
            s.instanceUpdated.asyncConnect(self._scaffoldUpdated)

        parent = root.find('parallelograms', namespaces=nsmap)
        for e in parent.findall('parallelogram', namespaces=nsmap):
            s = Parallelogram.fromElement(e)
            scaffolds[s.uuid] = s
            s.instanceUpdated.asyncConnect(self._scaffoldUpdated)

        parent = root.find('sphereScaffolds', namespaces=nsmap)
        for e in parent.findall('sphereScaffold', namespaces=nsmap):
            s = SphereScaffold.fromElement(e)
            scaffolds[s.uuid] = s
            s.instanceUpdated.asyncConnect(self._scaffoldUpdated)

        return scaffolds

    def getScaffolds(self):
        return self._scaffolds

    def getScaffold(self, uuid: UUID):
        return self._scaffolds[uuid]

    def hasScaffold(self, uuid: UUID):
        return uuid in self._scaffolds

    async def addScaffold(self, scaffold: Scaffold):
        if scaffold.uuid in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, BoundaryScaffold):
            parent = self.SCAFFOLDS_PATH + '/boundaries'
        elif isinstance(scaffold, IsoSurface):
            parent = self.SCAFFOLDS_PATH + '/isoSurfaces'
        elif isinstance(scaffold, DiskScaffold):
            parent = self.SCAFFOLDS_PATH + '/diskScaffolds'
        elif isinstance(scaffold, LineScaffold):
            parent = self.SCAFFOLDS_PATH + '/lineScaffolds'
        elif isinstance(scaffold, Parallelogram):
            parent = self.SCAFFOLDS_PATH + '/parallelograms'
        elif isinstance(scaffold, SphereScaffold):
            parent = self.SCAFFOLDS_PATH + '/sphereScaffolds'
        else:
            raise AssertionError

        coredb.CoreDB().addElement(parent, scaffold.toElement())

        self._scaffolds[scaffold.uuid] = scaffold

        scaffold.instanceUpdated.asyncConnect(self._scaffoldUpdated)

        await self.scaffoldAdded.emit(scaffold.uuid)

    async def removeScaffold(self, scaffold: Scaffold):
        if scaffold.uuid not in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, BoundaryScaffold):
            parent = self.SCAFFOLDS_PATH + '/boundaries'
        elif isinstance(scaffold, IsoSurface):
            parent = self.SCAFFOLDS_PATH + '/isoSurfaces'
        elif isinstance(scaffold, DiskScaffold):
            parent = self.SCAFFOLDS_PATH + '/diskScaffolds'
        elif isinstance(scaffold, LineScaffold):
            parent = self.SCAFFOLDS_PATH + '/lineScaffolds'
        elif isinstance(scaffold, Parallelogram):
            parent = self.SCAFFOLDS_PATH + '/parallelograms'
        elif isinstance(scaffold, SphereScaffold):
            parent = self.SCAFFOLDS_PATH + '/sphereScaffolds'
        else:
            raise AssertionError

        await self.removingScaffold.emit(scaffold.uuid)

        coredb.CoreDB().removeElement(parent + scaffold.xpath())

        del self._scaffolds[scaffold.uuid]

    async def _scaffoldUpdated(self, uuid: UUID):
        print('scaffold updated')
        if uuid not in self._scaffolds:
            return

        scaffold = self._scaffolds[uuid]

        if isinstance(scaffold, BoundaryScaffold):
            parent = self.SCAFFOLDS_PATH + '/boundaries'
        elif isinstance(scaffold, IsoSurface):
            parent = self.SCAFFOLDS_PATH + '/isoSurfaces'
        elif isinstance(scaffold, DiskScaffold):
            parent = self.SCAFFOLDS_PATH + '/diskScaffolds'
        elif isinstance(scaffold, LineScaffold):
            parent = self.SCAFFOLDS_PATH + '/lineScaffolds'
        elif isinstance(scaffold, Parallelogram):
            parent = self.SCAFFOLDS_PATH + '/parallelograms'
        elif isinstance(scaffold, SphereScaffold):
            parent = self.SCAFFOLDS_PATH + '/sphereScaffolds'
        else:
            raise AssertionError

        coredb.CoreDB().removeElement(parent + scaffold.xpath())
        coredb.CoreDB().addElement(parent, scaffold.toElement())

        await self.scaffoldUpdated.emit(scaffold.uuid)

    # def getBoundariesInUse(self):
    #     boundaries = []

    #     for scaffold in self._scaffolds.values():
    #         if isinstance(scaffold, BoundaryScaffold):
    #             boundaries.append(scaffold.bcid)

    #     return boundaries

    def nameDuplicates(self, uuid: UUID, name: str) -> bool:
        for scaffold in self._scaffolds.values():
            if scaffold.name == name and scaffold.uuid != uuid:
                return True

        return False

    def getNewBoundaryScaffoldName(self) -> str:
        return self._getNewScaffoldName(BOUNDARY_SCAFFOLD_NAME_PREFIX)

    def getNewIsoSurfaceName(self) -> str:
        return self._getNewScaffoldName(ISO_SURFACE_NAME_PREFIX)

    def getNewDiskName(self) -> str:
        return self._getNewScaffoldName(DISK_SCAFFOLD_NAME_PREFIX)

    def getNewLineName(self) -> str:
        return self._getNewScaffoldName(LINE_SCAFFOLD_NAME_PREFIX)

    def getNewParallelogramName(self) -> str:
        return self._getNewScaffoldName(PARALLELOGRAM_NAME_PREFIX)

    def getNewSphereName(self) -> str:
        return self._getNewScaffoldName(SPHERE_SCAFFOLD_NAME_PREFIX)

    def _getNewScaffoldName(self, prefix: str) -> str:
        suffixes = [scaffold.name[len(prefix):] for scaffold in self._scaffolds.values() if scaffold.name.startswith(prefix)]
        for i in range(1, 1000):
            if f'-{i}' not in suffixes:
                return f'{prefix}-{i}'
        return f'{prefix}-{uuid4()}'


