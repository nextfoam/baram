#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .mrf_widget_ui import Ui_MRFWidget


class MRFWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_MRFWidget()
        self._ui.setupUi(self)
        self.setVisible(False)
