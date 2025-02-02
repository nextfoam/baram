#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

from baramFlow.coredb.visual_report import VisualReport
from baramFlow.coredb.visual_reports_db import VisualReportsDB

from .contour_dialog import ContourDialog

from .visual_report_widget_ui import Ui_VisualReportWidget


class VisualReportWidget(QWidget):
    def __init__(self, report: VisualReport):
        super().__init__()

        self._ui = Ui_VisualReportWidget()
        self._ui.setupUi(self)

        self._report = report
        self._dialog = None

        self.load()

    @property
    def name(self):
        return self._report.name

    @property
    def report(self):
        return self._report

    def load(self):
        raise NotImplementedError


class ContourWidget(VisualReportWidget):
    def __init__(self, report: VisualReport):
        super().__init__(report)

        self._ui.type.setText('Contour')

    def load(self):
        self._ui.name.setText(self._report.name)

    def edit(self):
        self._dialog = ContourDialog(self, self._report, isNew=False)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()

    def _editAccepted(self):
        VisualReportsDB().updateVisualReport(self._report)
        self.load()

