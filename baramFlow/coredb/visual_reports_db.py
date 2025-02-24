#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from uuid import UUID, uuid4

from PySide6.QtCore import QObject, Signal


from baramFlow.coredb import coredb
from baramFlow.coredb.contour import Contour

from baramFlow.coredb.libdb import nsmap

from baramFlow.coredb.visual_report import VisualReport



CONTOUR_NAME_PREFIX = 'contour'


_mutex = Lock()


class VisualReportsDB(QObject):
    ReportAdded    = Signal(UUID)
    ReportUpdated  = Signal(UUID)
    RemovingReport = Signal(UUID)

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

        super().__init__()

        self._reports: dict[UUID, VisualReport] = {}

    def load(self):
         for report in self._reports.values():
            self.RemovingReport.emit(report.uuid)

         self._reports = self._parseVisualReports()

         for report in self._reports.values():
            self.ReportAdded.emit(report.uuid)

    def _parseVisualReports(self) -> dict[UUID, VisualReport]:
        reports = {}
        parent = coredb.CoreDB().getElement(self.VISUAL_REPORTS_PATH)

        contours = parent.find('contours', namespaces=nsmap)
        for e in contours.findall('contour', namespaces=nsmap):
            c = Contour.fromElement(e)
            reports[c.uuid] = c

        return reports

    def getVisualReports(self):
        return self._reports

    def getVisualReport(self, uuid: UUID):
        return self._reports[uuid]

    def addVisualReport(self, report: VisualReport):
        if report.uuid in self._reports:
            raise AssertionError

        if isinstance(report, Contour):
            parent = self.VISUAL_REPORTS_PATH + '/contours'
        else:
            raise AssertionError

        coredb.CoreDB().addElement(parent, report.toElement())

        self._reports[report.uuid] = report

        self.ReportAdded.emit(report.uuid)

    def removeVisualReport(self, report: VisualReport):
        if report.uuid not in self._reports:
            raise AssertionError

        if isinstance(report, Contour):
            parent = self.VISUAL_REPORTS_PATH + '/contours'
        else:
            raise AssertionError

        self.RemovingReport.emit(report.uuid)

        coredb.CoreDB().removeElement(parent + report.xpath())

        del self._reports[report.uuid]

    def updateVisualReport(self, report: VisualReport):
        if report.uuid not in self._reports:
            raise AssertionError

        if isinstance(report, Contour):
            parent = self.VISUAL_REPORTS_PATH + '/contours'
        else:
            raise AssertionError

        coredb.CoreDB().removeElement(parent + report.xpath())
        coredb.CoreDB().addElement(parent, report.toElement())

        self.ReportUpdated.emit(report.uuid)

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


