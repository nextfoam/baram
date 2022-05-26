#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .open_channel_outlet_dialog_ui import Ui_OpenChannelOutletDialog
from .turbulence_model import TurbulenceModel


class OpenChannelOutletDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_OpenChannelOutletDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
