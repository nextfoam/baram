#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

from .visual_report_widget_ui import Ui_VisualReportWidget


class VisualReportWidget(QWidget):
    def __init__(self):
        super().__init__()

        self._ui = Ui_VisualReportWidget()
        self._ui.setupUi(self)

    async def edit(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError
