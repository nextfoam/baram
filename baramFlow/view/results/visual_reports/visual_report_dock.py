#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6QtAds import CDockWidget

from baramFlow.coredb.visual_report import VisualReport

from .visual_report_view import VisualReportView


class VisualReportDock(CDockWidget):
    def __init__(self, report: VisualReport):
        super().__init__(report.name)

        self._widget = VisualReportView(self, report)
        self.setWidget(self._widget)


