#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from uuid import UUID, uuid4

from baramFlow.coredb import coredb
from baramFlow.coredb.contour import Contour

from baramFlow.coredb.libdb import nsmap

from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.coredb.visual_report import VisualReport
from baramFlow.view.results.visual_reports.openfoam_reader import OpenFOAMReader
from libbaram.async_signal import AsyncSignal
from libbaram.openfoam.polymesh import collectInternalMesh


CONTOUR_NAME_PREFIX = 'contour'


_mutex = Lock()


class VisualReportsDB:
    VISUAL_REPORTS_PATH = '/visualReports'

    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(VisualReportsDB, cls).__new__(cls, *args, **kwargs)

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

        self._reports: dict[UUID, VisualReport] = {}

    async def load(self):
        self._reports = await self._parseVisualReports()

        for report in self._reports.values():
            report.instanceUpdated.asyncConnect(self._reportUpdated)
            await self.reportAdded.emit(report.uuid)

    async def close(self):
        for report in self._reports.values():
            await self.removingReport.emit(report.uuid)

        self._reports = {}

    async def _parseVisualReports(self) -> dict[UUID, VisualReport]:
        reports = {}
        parent = coredb.CoreDB().getElement(self.VISUAL_REPORTS_PATH)

        contours = parent.find('contours', namespaces=nsmap)
        for e in contours.findall('contour', namespaces=nsmap):
            c = Contour.fromElement(e)
            reports[c.uuid] = c

            if len(c.reportingScaffolds) == 0:
                continue

            async with OpenFOAMReader() as reader:
                reader.setTimeValue(float(c.time))
                await reader.update()
                mBlock = reader.getOutput()
                c.polyMesh = mBlock
                c.internalMesh = collectInternalMesh(mBlock)
                for rs in c.reportingScaffolds.values():
                    scaffold = ScaffoldsDB().getScaffold(rs.scaffoldUuid)
                    rs.dataSet = await scaffold.getDataSet(mBlock)

        return reports

    def getVisualReports(self):
        return self._reports

    def getVisualReport(self, uuid: UUID):
        return self._reports[uuid]

    async def addVisualReport(self, report: VisualReport):
        if report.uuid in self._reports:
            raise AssertionError

        report.saveToCoreDB()

        self._reports[report.uuid] = report

        report.instanceUpdated.asyncConnect(self._reportUpdated)

        await self.reportAdded.emit(report.uuid)

    async def removeVisualReport(self, report: VisualReport):
        if report.uuid not in self._reports:
            raise AssertionError

        if isinstance(report, Contour):
            parent = self.VISUAL_REPORTS_PATH + '/contours'
        else:
            raise AssertionError

        await self.removingReport.emit(report.uuid)

        coredb.CoreDB().removeElement(parent + report.xpath())

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

    def getNewContourName(self) -> str:
        return self._getNewVisualReportName(CONTOUR_NAME_PREFIX)

    def _getNewVisualReportName(self, prefix: str) -> str:
        suffixes = [v.name[len(prefix):] for v in self._reports.values() if v.name.startswith(prefix)]
        for i in range(1, 1000):
            if f'-{i}' not in suffixes:
                return f'{prefix}-{i}'
        return f'{prefix}-{uuid4()}'


