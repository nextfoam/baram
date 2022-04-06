#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.dialog.baram_dialog import BaramDialog
from .viscous_model_dialog_ui import Ui_ViscousModelDialog


class ViscousModelDialog(BaramDialog):
    def __init__(self):
        super().__init__(Ui_ViscousModelDialog())

    def connectSignalsSlots(self):
        self._ui.laminar.toggled.connect(self.modelChanged)
        self._ui.kEpsilon.toggled.connect(self.modelChanged)
        self._ui.kOmega.toggled.connect(self.modelChanged)
        self._ui.spalartAllmaras.toggled.connect(self.modelChanged)

    def modelChanged(self):
        self._ui.kEpsilonModel.setVisible(self._ui.kEpsilon.isChecked())
        self._ui.kOmegaModel.setVisible(self._ui.kOmega.isChecked())
        self._resizeDialog(self._ui.modelWidget)
