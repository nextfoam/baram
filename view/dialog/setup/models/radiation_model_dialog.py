#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.dialog.baram_dialog import BaramDialog
from .radiation_model_dialog_ui import Ui_RadiationModelDialog


class RadiationModelDialog(BaramDialog):
    def __init__(self):
        super().__init__(Ui_RadiationModelDialog())
        self._doGroup = [
            self._ui.flowIterationsPerRadiationIterationLabel,
            self._ui.flowIterationsPerRadiationIteration,
            self._ui.phiDivisionsLabel,
            self._ui.phiDivisions,
            self._ui.thetaDivisionsLabel,
            self._ui.thetaDivisions,
            self._ui.residualConvergenceCriteriaLabel,
            self._ui.residualConvergenceCriteria,
            self._ui.maximumNumberOfRadiationIterationsLabel,
            self._ui.maximumNumberOfRadiationIterations,
        ]

    def connectSignalsSlots(self):
        self._ui.off.toggled.connect(self.modelChanged)
        self._ui.p1.toggled.connect(self.modelChanged)
        self._ui.DO.toggled.connect(self.modelChanged)

    def modelChanged(self):
        self._ui.parametersWidget.setVisible(not self._ui.off.isChecked())
        self._setVisible(self._doGroup, self._ui.DO.isChecked())
        self._resizeDialog(self._ui.parametersGroup)

