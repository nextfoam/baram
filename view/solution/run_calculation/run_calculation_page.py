#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from coredb import coredb
from .run_calculation_page_ui import Ui_RunCalculationPage


class RunCalculationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_RunCalculationPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._connectSignalsSlots()

        self._load()

    def hideEvent(self, ev):
        if ev.spontaneous():
            return

    def _connectSignalsSlots(self):
        pass

    def _load(self):
        return
