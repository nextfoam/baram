#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .open_channel_outlet_dialog_ui import Ui_OpenChannelOutletDialog
from .turbulence_model import TurbulenceModel


class OpenChannelOutletDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_OpenChannelOutletDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)

        self._setup()

    def _setup(self):
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
