#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from uuid import UUID, uuid4

from baramFlow.coredb import coredb
from baramFlow.coredb.iso_surface import IsoSurface
from baramFlow.coredb.libdb import nsmap

from baramFlow.coredb.scaffold import Scaffold


ISO_SURFACE_NAME_PREFIX = 'iso-surface'


_mutex = Lock()


class ScaffoldsDB():
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

        super().__init__()

        self._scaffolds: dict[UUID, Scaffold] = {}


    def load(self):
        self._scaffolds = self._parseScaffolds()

    def _parseScaffolds(self) -> dict[UUID, Scaffold]:
        scaffolds = {}
        parent = coredb.CoreDB().getElement(self.SCAFFOLDS_PATH)

        isoSurfaces = parent.find('isoSurfaces', namespaces=nsmap)
        for e in isoSurfaces.findall('surface', namespaces=nsmap):
            s = IsoSurface.fromElement(e)
            scaffolds[s.uuid] = s

        return scaffolds

    def getScaffolds(self):
        return self._scaffolds

    def addScaffold(self, scaffold: Scaffold):
        if scaffold.uuid in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, IsoSurface):
            parent = self.SCAFFOLDS_PATH + '/isoSurfaces'
        else:
            raise AssertionError

        coredb.CoreDB().addElement(parent, scaffold.toElement())

        self._scaffolds[scaffold.uuid] = scaffold

    def removeScaffold(self, scaffold: Scaffold):
        if scaffold.uuid not in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, IsoSurface):
            parent = self.SCAFFOLDS_PATH + '/isoSurfaces'
        else:
            raise AssertionError

        coredb.CoreDB().removeElement(parent + f'/surface[uuid="{str(scaffold.uuid)}"]')

        del self._scaffolds[scaffold.uuid]

    def updateScaffold(self, scaffold: Scaffold):
        if scaffold.uuid not in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, IsoSurface):
            parent = self.SCAFFOLDS_PATH + '/isoSurfaces'
        else:
            raise AssertionError

        coredb.CoreDB().removeElement(parent + f'/surface[uuid="{str(scaffold.uuid)}"]')
        coredb.CoreDB().addElement(parent, scaffold.toElement())

    def nameDuplicates(self, uuid: UUID, name: str) -> bool:
        for v in self._scaffolds.values():
            if v.name == name and v.uuid != uuid:
                return True

        return False

    def getNewIsoSurfaceName(self) -> str:
        return self._getNewScaffoldName(ISO_SURFACE_NAME_PREFIX)

    def _getNewScaffoldName(self, prefix: str) -> str:
        suffixes = [v.name[len(prefix):] for v in self._scaffolds.values() if v.name.startswith(prefix)]
        for i in range(1, 1000):
            if f'-{i}' not in suffixes:
                return f'{prefix}-{i}'
        return f'{prefix}-{uuid4()}'


