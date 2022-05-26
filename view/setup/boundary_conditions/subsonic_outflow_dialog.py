#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .subsonic_outflow_dialog_ui import Ui_SubsonicOutflowDialog


class SubsonicOutflowDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_SubsonicOutflowDialog()
        self._ui.setupUi(self)
