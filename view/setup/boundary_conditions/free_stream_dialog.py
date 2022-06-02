#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .free_stream_dialog_ui import Ui_FreeStreamDialog
from .turbulence_model import TurbulenceModel


class FreeStreamDialog(ResizableDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_FreeStreamDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
