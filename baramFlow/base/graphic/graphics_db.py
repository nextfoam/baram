#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from uuid import UUID, uuid4

from baramFlow.coredb import coredb
from baramFlow.base.graphic.graphic import Graphic

from baramFlow.coredb.libdb import nsmap

from libbaram.async_signal import AsyncSignal


GRAPHICS_NAME_PREFIX = 'Graphics'


_mutex = Lock()


class GraphicsDB:
    GRAPHICS_PATH = '/graphics'

    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(GraphicsDB, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        with _mutex:
            if hasattr(self, '_initialized'):
                return
            else:
                self._initialized = True

        self.reportAdded    = AsyncSignal(UUID)
        self.reportUpdated  = AsyncSignal(UUID)
        self.removingReport = AsyncSignal(UUID)

        self._reports: dict[UUID, Graphic] = {}

    async def load(self):
        self._reports = await self._parseGraphics()

        for report in self._reports.values():
            report.instanceUpdated.asyncConnect(self._reportUpdated)
            await self.reportAdded.emit(report.uuid)

    async def close(self):
        for report in self._reports.values():
            await self.removingReport.emit(report.uuid)

        self._reports = {}

    async def _parseGraphics(self) -> dict[UUID, Graphic]:
        reports = {}
        parent = coredb.CoreDB().getElement(self.GRAPHICS_PATH)

        for e in parent.findall('graphic', namespaces=nsmap):
            c = Graphic.fromElement(e)
            reports[c.uuid] = c

            if len(c.getScaffolds()) == 0:
                continue

            await c.updatePolyMesh()

        return reports

    def isScaffoldUsed(self, scaffoldUuid: UUID) -> bool:
        for report in self._reports.values():
            if report.hasScaffold(scaffoldUuid):
                return True

        return False

    async def updatePolyMeshAll(self):
        for report in self._reports.values():
            await report.updatePolyMesh()

    def getVisualReports(self):
        return self._reports

    def getVisualReport(self, uuid: UUID):
        return self._reports[uuid]

    async def addVisualReport(self, report: Graphic):
        if report.uuid in self._reports:
            raise AssertionError

        report.saveToCoreDB()

        self._reports[report.uuid] = report

        report.instanceUpdated.asyncConnect(self._reportUpdated)

        await self.reportAdded.emit(report.uuid)

    async def removeVisualReport(self, report: Graphic):
        if report.uuid not in self._reports:
            raise AssertionError

        await self.removingReport.emit(report.uuid)

        coredb.CoreDB().removeElement(self.GRAPHICS_PATH + report.xpath())

        del self._reports[report.uuid]

    async def _reportUpdated(self, uuid: UUID):
        if uuid not in self._reports:
            return

        report = self._reports[uuid]

        await self.reportUpdated.emit(report.uuid)

    def nameDuplicates(self, uuid: UUID, name: str) -> bool:
        for v in self._reports.values():
            if v.name == name and v.uuid != uuid:
                return True

        return False

    def getNewGraphicName(self) -> str:
        return self._getNewVisualReportName(GRAPHICS_NAME_PREFIX)

    def _getNewVisualReportName(self, prefix: str) -> str:
        suffixes = [v.name[len(prefix):] for v in self._reports.values() if v.name.startswith(prefix)]
        for i in range(1, 1000):
            if f'-{i}' not in suffixes:
                return f'{prefix}-{i}'
        return f'{prefix}-{uuid4()}'


