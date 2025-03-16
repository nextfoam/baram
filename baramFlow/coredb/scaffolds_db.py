#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from uuid import UUID, uuid4

from PySide6.QtCore import QObject, Signal

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_scaffold import BoundaryScaffold
from baramFlow.coredb.iso_surface import IsoSurface
from baramFlow.coredb.libdb import nsmap

from baramFlow.coredb.scaffold import Scaffold


BOUNDARY_SCAFFOLD_NAME_PREFIX = 'boundary'
ISO_SURFACE_NAME_PREFIX = 'iso-surface'


_mutex = Lock()


class ScaffoldsDB(QObject):
    SCAFFOLDS_PATH = '/scaffolds'

    ScaffoldAdded = Signal(UUID)
    ScaffoldUpdated = Signal(UUID)
    RemovingScaffold = Signal(UUID)

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

        super().__init__()

        self._scaffolds: dict[UUID, Scaffold] = {}


    def load(self):
        self._scaffolds = self._parseScaffolds()

    def _parseScaffolds(self) -> dict[UUID, Scaffold]:
        scaffolds = {}
        parent = coredb.CoreDB().getElement(self.SCAFFOLDS_PATH)

        boundaries = parent.find('boundaries', namespaces=nsmap)
        for e in boundaries.findall('boundary', namespaces=nsmap):
            s = BoundaryScaffold.fromElement(e)
            scaffolds[s.uuid] = s
            s.instanceUpdated.connect(self._scaffoldUpdated)

        isoSurfaces = parent.find('isoSurfaces', namespaces=nsmap)
        for e in isoSurfaces.findall('surface', namespaces=nsmap):
            s = IsoSurface.fromElement(e)
            scaffolds[s.uuid] = s
            s.instanceUpdated.connect(self._scaffoldUpdated)

        return scaffolds

    def getScaffolds(self):
        return self._scaffolds

    def getScaffold(self, uuid: UUID):
        return self._scaffolds[uuid]

    def hasScaffold(self, uuid: UUID):
        return uuid in self._scaffolds

    def addScaffold(self, scaffold: Scaffold):
        if scaffold.uuid in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, BoundaryScaffold):
            parent = self.SCAFFOLDS_PATH + '/boundaries'
        elif isinstance(scaffold, IsoSurface):
            parent = self.SCAFFOLDS_PATH + '/isoSurfaces'
        else:
            raise AssertionError

        coredb.CoreDB().addElement(parent, scaffold.toElement())

        self._scaffolds[scaffold.uuid] = scaffold

        scaffold.instanceUpdated.connect(self._scaffoldUpdated)

        self.ScaffoldAdded.emit(scaffold.uuid)

    def removeScaffold(self, scaffold: Scaffold):
        if scaffold.uuid not in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, BoundaryScaffold):
            parent = self.SCAFFOLDS_PATH + '/boundaries'
        elif isinstance(scaffold, IsoSurface):
            parent = self.SCAFFOLDS_PATH + '/isoSurfaces'
        else:
            raise AssertionError

        self.RemovingScaffold.emit(scaffold.uuid)

        coredb.CoreDB().removeElement(parent + scaffold.xpath())

        del self._scaffolds[scaffold.uuid]

    def _scaffoldUpdated(self, uuid: UUID):
        print('scaffold updated')
        if uuid not in self._scaffolds:
            return

        scaffold = self._scaffolds[uuid]

        if isinstance(scaffold, BoundaryScaffold):
            parent = self.SCAFFOLDS_PATH + '/boundaries'
        elif isinstance(scaffold, IsoSurface):
            parent = self.SCAFFOLDS_PATH + '/isoSurfaces'
        else:
            raise AssertionError

        coredb.CoreDB().removeElement(parent + scaffold.xpath())
        coredb.CoreDB().addElement(parent, scaffold.toElement())

        self.ScaffoldUpdated.emit(scaffold.uuid)

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

    def _getNewScaffoldName(self, prefix: str) -> str:
        suffixes = [scaffold.name[len(prefix):] for scaffold in self._scaffolds.values() if scaffold.name.startswith(prefix)]
        for i in range(1, 1000):
            if f'-{i}' not in suffixes:
                return f'{prefix}-{i}'
        return f'{prefix}-{uuid4()}'


