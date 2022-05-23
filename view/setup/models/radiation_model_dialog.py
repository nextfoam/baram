#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from view.widgets.resizable_dialog import ResizableDialog, ResizableForm
from .radiation_model_dialog_ui import Ui_RadiationModelDialog


class RadiationModelDialog(ResizableDialog):
    class PARAMETER_FORM_ROW(Enum):
        FLOW_ITERATIONS_PER_RADIATION_ITERATION = 0
        ABSORPTION_COEFFICIENT = auto()
        PHI_DIVISIONS = auto()
        THEATA_DIVISIONS = auto()
        RESIDUAL_CONVERGENCE_CRITERIA = auto()
        MAXIMUM_NUMBER_OF_RADIATION_ITERATIONS = auto()

    def __init__(self):
        super().__init__()
        self._ui = Ui_RadiationModelDialog()
        self._ui.setupUi(self)

        self._parameterLayout = ResizableForm(self._ui.parametersGroup.layout())
        self._doGroup = [
            self.PARAMETER_FORM_ROW.PHI_DIVISIONS.value,
            self.PARAMETER_FORM_ROW.THEATA_DIVISIONS.value,
            self.PARAMETER_FORM_ROW.RESIDUAL_CONVERGENCE_CRITERIA.value,
            self.PARAMETER_FORM_ROW.MAXIMUM_NUMBER_OF_RADIATION_ITERATIONS.value,
        ]

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.off.toggled.connect(self._modelChanged)
        self._ui.p1.toggled.connect(self._modelChanged)
        self._ui.DO.toggled.connect(self._modelChanged)

    def _modelChanged(self):
        self._ui.parametersWidget.setVisible(not self._ui.off.isChecked())
        self._parameterLayout.setRowsVisible(self._doGroup, self._ui.DO.isChecked())
        self._resizeDialog(self._ui.parametersGroup)

