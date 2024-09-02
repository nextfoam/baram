#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
import logging

from baramFlow.view.widgets.content_page import ContentPage

from .force_report_dialog import ForceReportDialog
from .point_report_dialog import PointReportDialog
from .surface_report_dialog import SurfaceReportDialog
from .volume_report_dialog import VolumeReportDialog

from .reports_page_ui import Ui_ReportsPage


logger = logging.getLogger(__name__)


class ReportsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ReportsPage()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _load(self):
        pass

    def _connectSignalsSlots(self):
        self._ui.forceReport.clicked.connect(self._forceReportClicked)
        self._ui.pointReport.clicked.connect(self._pointReportClicked)
        self._ui.surfaceReport.clicked.connect(self._surfaceReportClicked)
        self._ui.volumeReport.clicked.connect(self._volumeReportClicked)

    @qasync.asyncSlot()
    async def _forceReportClicked(self):
        self._dialog = ForceReportDialog(self)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _pointReportClicked(self):
        self._dialog = PointReportDialog(self)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _surfaceReportClicked(self):
        self._dialog = SurfaceReportDialog(self)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _volumeReportClicked(self):
        self._dialog = VolumeReportDialog(self)
        self._dialog.open()
