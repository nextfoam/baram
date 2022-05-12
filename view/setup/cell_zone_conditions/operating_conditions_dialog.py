#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .operating_conditions_dialog_ui import Ui_OperatingConditionsDialog


class OperatingConditionsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_OperatingConditionsDialog()
        self._ui.setupUi(self)
