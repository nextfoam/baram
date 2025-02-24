#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from uuid import UUID, uuid4

from baramFlow.app import app
from baramFlow.coredb.contour import Contour

from baramFlow.coredb.visual_reports_db import VisualReportsDB
from baramFlow.view.results.visual_reports.visual_report_dock import VisualReportDock


ISO_SURFACE_NAME_PREFIX = 'iso-surface'


_mutex = Lock()


class VisualReportDockManager():
    SCAFFOLDS_PATH = '/scaffolds'
    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(VisualReportDockManager, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        with _mutex:
            if hasattr(self, '_initialized'):
                return
            else:
                self._initialized = True

        super().__init__()

        self._docks: dict[UUID, VisualReportDock] = {}

        VisualReportsDB().ReportAdded.connect(self._reportAdded)
        VisualReportsDB().ReportUpdated.connect(self._reportUpdated)
        VisualReportsDB().RemovingReport.connect(self._reportRemoving)


    def load(self):
        for report in VisualReportsDB().getVisualReports().values():
            if isinstance(report, Contour):
                self._addNewReportDock(report)

    def _addNewReportDock(self, report):
        dock = VisualReportDock(report)
        self._docks[report.uuid] = dock
        app.window.addDockWidget(dock)

    def _reportAdded(self, uuid: UUID):
        report = VisualReportsDB().getVisualReport(uuid)
        self._addNewReportDock(report)

    def _reportUpdated(self, uuid: UUID):
        if uuid in self._docks:
            dock = self._docks[uuid]
            # ToDo: what to do?

    def _reportRemoving(self, uuid: UUID):
        if uuid in self._docks:
            app.window.removeDockWidget(self._docks[uuid])
            del self._docks[uuid]
