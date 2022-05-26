#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .ABL_inlet_dialog_ui import Ui_ABLInletDialog


class ABLInletDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_ABLInletDialog()
        self._ui.setupUi(self)
