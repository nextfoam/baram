#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .far_field_riemann_dialog_ui import Ui_PressureFarFieldDialog
from .turbulence_model import TurbulenceModel


class FarFieldRiemannDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_PressureFarFieldDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)

        self._setup()

    def _setup(self):
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
