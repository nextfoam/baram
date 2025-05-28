#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from typing import cast
from uuid import UUID, uuid4

from PySide6.QtCore import QCoreApplication

from baramFlow.base.scaffold.boundary_scaffold import BoundaryScaffold
from baramFlow.base.scaffold.disk_scaffold import DiskScaffold
from baramFlow.base.scaffold.iso_surface import IsoSurface

from baramFlow.base.scaffold.line_scaffold import LineScaffold
from baramFlow.base.scaffold.parallelogram import Parallelogram
from baramFlow.base.scaffold.plane_scaffold import PlaneScaffold
from baramFlow.base.scaffold.scaffold import Scaffold
from baramFlow.base.scaffold.sphere_scaffold import SphereScaffold
from libbaram.async_signal import AsyncSignal


BOUNDARY_SCAFFOLD_NAME_PREFIX = 'boundary'
DISK_SCAFFOLD_NAME_PREFIX = 'disk-scaffold'
ISO_SURFACE_NAME_PREFIX = 'iso-surface'
LINE_SCAFFOLD_NAME_PREFIX = 'line-scaffold'
PARALLELOGRAM_NAME_PREFIX = 'parallelogram'
PLANE_SCAFFOLD_NAME_PREFIX = 'plane-scaffold'
SPHERE_SCAFFOLD_NAME_PREFIX = 'sphere-scaffold'

_mutex = Lock()


class ScaffoldsDB:
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
        scaffolds: dict[UUID, Scaffold] = {}

        scaffolds.update(BoundaryScaffold.parseScaffolds())
        scaffolds.update(DiskScaffold.parseScaffolds())
        scaffolds.update(IsoSurface.parseScaffolds())
        scaffolds.update(LineScaffold.parseScaffolds())
        scaffolds.update(Parallelogram.parseScaffolds())
        scaffolds.update(PlaneScaffold.parseScaffolds())
        scaffolds.update(SphereScaffold.parseScaffolds())

        for s in scaffolds.values():
            s.instanceUpdated.asyncConnect(self._scaffoldUpdated)

        self._scaffolds = scaffolds

    def getScaffolds(self):
        return self._scaffolds

    def getScaffold(self, uuid: UUID):
        return self._scaffolds[uuid]

    def hasScaffold(self, uuid: UUID):
        return uuid in self._scaffolds

    async def addScaffold(self, scaffold: Scaffold):
        if scaffold.uuid in self._scaffolds:
            raise AssertionError

        scaffold.addElement()

        self._scaffolds[scaffold.uuid] = scaffold

        scaffold.instanceUpdated.asyncConnect(self._scaffoldUpdated)

        await self.scaffoldAdded.emit(scaffold.uuid)

    async def removeScaffold(self, scaffold: Scaffold):
        if scaffold.uuid not in self._scaffolds:
            raise AssertionError

        await self.removingScaffold.emit(scaffold.uuid)

        scaffold.removeElement()

        del self._scaffolds[scaffold.uuid]

    async def _scaffoldUpdated(self, uuid: UUID):
        print('scaffold updated')
        if uuid not in self._scaffolds:
            return

        scaffold = self._scaffolds[uuid]

        scaffold.removeElement()
        scaffold.addElement()

        await self.scaffoldUpdated.emit(scaffold.uuid)

    async def refreshAllScaffolds(self):
        for scaffold in self._scaffolds.values():
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

    def getNewDiskName(self) -> str:
        return self._getNewScaffoldName(DISK_SCAFFOLD_NAME_PREFIX)

    def getNewIsoSurfaceName(self) -> str:
        return self._getNewScaffoldName(ISO_SURFACE_NAME_PREFIX)

    def getNewLineName(self) -> str:
        return self._getNewScaffoldName(LINE_SCAFFOLD_NAME_PREFIX)

    def getNewParallelogramName(self) -> str:
        return self._getNewScaffoldName(PARALLELOGRAM_NAME_PREFIX)

    def getNewPlaneName(self) -> str:
        return self._getNewScaffoldName(PLANE_SCAFFOLD_NAME_PREFIX)

    def getNewSphereName(self) -> str:
        return self._getNewScaffoldName(SPHERE_SCAFFOLD_NAME_PREFIX)

    def _getNewScaffoldName(self, prefix: str) -> str:
        suffixes = [scaffold.name[len(prefix):] for scaffold in self._scaffolds.values() if scaffold.name.startswith(prefix)]
        for i in range(1, 1000):
            if f'-{i}' not in suffixes:
                return f'{prefix}-{i}'
        return f'{prefix}-{uuid4()}'

    def scaffoldTypeString(self, uuid: UUID):
        if uuid not in self._scaffolds:
            return None

        scaffold = self._scaffolds[uuid]
        if isinstance(scaffold, BoundaryScaffold):
            return QCoreApplication.translate('Scaffold', 'Boundary')
        elif isinstance(scaffold, DiskScaffold):
            return QCoreApplication.translate('Scaffold', 'Disk')
        elif isinstance(scaffold, IsoSurface):
            return QCoreApplication.translate('Scaffold', 'Iso-surface')
        elif isinstance(scaffold, LineScaffold):
            return QCoreApplication.translate('Scaffold', 'Line')
        elif isinstance(scaffold, Parallelogram):
            return QCoreApplication.translate('Scaffold', 'Parallelogram')
        elif isinstance(scaffold, PlaneScaffold):
            return QCoreApplication.translate('Scaffold', 'Plane')
        elif isinstance(scaffold, SphereScaffold):
            return QCoreApplication.translate('Scaffold', 'Sphere')
        else:
            return None


    def rematchBoundaries(self):
        for scaffold in self._scaffolds.values():
            if isinstance(scaffold, BoundaryScaffold):
                cast(BoundaryScaffold, scaffold).rematchBoundaries()

