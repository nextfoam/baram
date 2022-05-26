#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .pressure_outlet_dialog_ui import Ui_PressureOutletDialog
from .turbulence_model import TurbulenceModel


class PressureOutletDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_PressureOutletDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)

        self._setup()
        self._connectSignalsSlots()

        self._energyModelOn = False
        self._calculateBackFlowToggled()

    def _setup(self):
        layout = self._ui.calculateBackflow.layout()
        layout.insertWidget(0, self._turbulenceWidget)

    def _connectSignalsSlots(self):
        self._ui.calculateBackflow.toggled.connect(self._calculateBackFlowToggled)

    def _calculateBackFlowToggled(self):
        self._ui.backflowTotalTemperature.setEnabled(self._energyModelOn)

