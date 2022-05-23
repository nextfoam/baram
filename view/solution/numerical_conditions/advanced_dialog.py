#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .advanced_dialog_ui import Ui_AdvancedDialog


class AdvancedDialog(QDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_AdvancedDialog()
        self._ui.setupUi(self)
