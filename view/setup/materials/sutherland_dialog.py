#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .sutherland_dialog_ui import Ui_SutherlandDialog

class SutherlandDialog(QDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_SutherlandDialog()
        self._ui.setupUi(self)

    def coefficient(self):
        return self._ui.coefficient.text()

    def temperature(self):
        return self._ui.temperature.text()

