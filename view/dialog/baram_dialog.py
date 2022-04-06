#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog


class BaramDialog(QDialog):
    def __init__(self, ui):
        super().__init__()
        self._ui = ui
        self._ui.setupUi(self)
        self.connectSignalsSlots()

    def connectSignalsSlots(self):
        pass

    def _setVisible(self, widgetList, visible):
        for widget in widgetList:
            widget.setVisible(visible)

    def _resizeDialog(self, widget):
        while widget is not None:
            widget.adjustSize()
            widget = widget.parent()


