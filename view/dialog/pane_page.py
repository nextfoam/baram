#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget


class PanePage(QWidget):
    def __init__(self, ui):
        super().__init__()
        self._ui = ui
        self._ui.setupUi(self)

        self.connectSignalsSlots()

    def connectSignalsSlots(self):
        pass

    def load(self):
        pass

    def save(self):
        pass
