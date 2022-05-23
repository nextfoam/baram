#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from view.widgets.resizable_dialog import ResizableDialog
from .flow_rate_inlet_dialog_ui import Ui_FlowRateInletDialog
from .turbulence_model import TurbulenceModel
from .temperature_widget import TemperatureWidget


class FlowRateInletDialog(ResizableDialog):
    class FLOW_RATE_SPECIFICATION_METHOD(Enum):
        VOLUME_FLOW_RATE = 0
        MASS_FLOW_RATE = auto()

    def __init__(self):
        super().__init__()
        self._ui = Ui_FlowRateInletDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        self._temperatureWidget = TemperatureWidget(self)

        self._setup()
        self._connectSignalsSlots()

        self._flowRateSpecificationMethodChanged(0)

    def _setup(self):
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
        layout.addWidget(self._temperatureWidget)

    def _connectSignalsSlots(self):
        self._ui.flowRateSpecificationMethod.currentIndexChanged.connect(self._flowRateSpecificationMethodChanged)

    def _flowRateSpecificationMethodChanged(self, index):
        self._ui.volumeFlowRateWidget.setVisible(
            index == self.FLOW_RATE_SPECIFICATION_METHOD.VOLUME_FLOW_RATE.value
        )
        self._ui.massFlowRateWidget.setVisible(
            index == self.FLOW_RATE_SPECIFICATION_METHOD.MASS_FLOW_RATE.value
        )
        self._resizeDialog(self._ui.flowRate)