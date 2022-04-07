#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .viscous_model_dialog_ui import Ui_ViscousModelDialog


class ViscousModelDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ViscousModelDialog()
        self._ui.setupUi(self)

        self.connectSignalsSlots()

    def connectSignalsSlots(self):
        self._ui.laminar.toggled.connect(self.modelChanged)
        self._ui.kEpsilon.toggled.connect(self.modelChanged)
        self._ui.kOmega.toggled.connect(self.modelChanged)
        self._ui.spalartAllmaras.toggled.connect(self.modelChanged)

    def modelChanged(self):
        self._ui.kEpsilonModel.setVisible(self._ui.kEpsilon.isChecked())
        self._ui.kOmegaModel.setVisible(self._ui.kOmega.isChecked())
        self._resizeDialog(self._ui.modelWidget)
