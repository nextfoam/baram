#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog


class BaramDialog(QDialog):
    def __init__(self, ui):
        super().__init__()
        self._ui = ui
        self._ui.setupUi(self)
        self.connectSignalsSlots()
        self.initUI()

    # virtual
    def connectSignalsSlots(self):
        pass

    # virtual
    def initUI(self):
        pass

    def _resizeDialog(self, widget):
        while widget is not None:
            widget.adjustSize()
            widget = widget.parent()


