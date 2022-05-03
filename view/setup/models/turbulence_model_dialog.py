#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .turbulence_model_dialog_ui import Ui_TurbulenceModelDialog


class TurbulenceModelDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_TurbulenceModelDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.laminar.toggled.connect(self._modelChanged)
        self._ui.kEpsilon.toggled.connect(self._modelChanged)
        self._ui.kOmega.toggled.connect(self._modelChanged)
        self._ui.spalartAllmaras.toggled.connect(self._modelChanged)
        self._ui.LES.toggled.connect(self._modelChanged)

        self._ui.kEpsilon.toggled.connect(self._kEpsilonModelChanged)
        self._ui.standard.toggled.connect(self._kEpsilonModelChanged)
        self._ui.RNG.toggled.connect(self._kEpsilonModelChanged)
        self._ui.realizable.toggled.connect(self._kEpsilonModelChanged)

    def _modelChanged(self, checked):
        if checked:
            self._ui.kEpsilonModel.setVisible(self._ui.kEpsilon.isChecked())
            self._ui.kOmegaModel.setVisible(self._ui.kOmega.isChecked())
            self._resizeDialog(self._ui.modelWidget)

    def _kEpsilonModelChanged(self, checked):
        if checked:
            self._ui.nearWallTreatment.setVisible(self._ui.realizable.isChecked())
            self._resizeDialog(self._ui.kEpsilonModel)
