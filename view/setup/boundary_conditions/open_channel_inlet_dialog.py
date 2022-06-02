#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .open_channel_inlet_dialog_ui import Ui_OpenChannelInletDialog
from .turbulence_model import TurbulenceModel


class OpenChannelInletDialog(ResizableDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_OpenChannelInletDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
