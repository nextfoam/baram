#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .pressure_inlet_dialog_ui import Ui_PressureInletDialog
from .turbulence_model import TurbulenceModel
from .temperature_widget import TemperatureWidget


class PressureInletDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_PressureInletDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        self._temperatureWidget = TemperatureWidget(self)

        self._setup()

    def _setup(self):
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
        layout.addWidget(self._temperatureWidget)
