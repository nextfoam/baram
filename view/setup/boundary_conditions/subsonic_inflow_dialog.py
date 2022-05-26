#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .subsonic_inflow_dialog_ui import Ui_SubsonicInflowDialog
from .turbulence_model import TurbulenceModel


class SubsonicInflowDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_SubsonicInflowDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
