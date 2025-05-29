#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6QtAds import CDockWidget

from baramFlow.base.graphic.graphic import Graphic

from .graphic_view import VisualReportView


class GraphicDock(CDockWidget):
    def __init__(self, report: Graphic):
        super().__init__(report.name)

        self._widget = VisualReportView(self, report)
        self.setWidget(self._widget)

    def close(self):
        self._widget.close()
        super().close()

