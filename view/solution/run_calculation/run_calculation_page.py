#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .run_calculation_page_ui import Ui_RunCalculationPage


class RunCalculationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_RunCalculationPage()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        pass

    def load(self):
        pass

    def save(self):
        pass
