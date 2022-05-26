#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QTimer, QEvent
from PySide6.QtWidgets import QDialog

from .turbulence_dialog_ui import Ui_TurbulenceDialog


class Model(Enum):
    LAMINAR = auto()
    SPALART_ALLMARAS = auto()
    K_EPSILON = auto()
    K_OMEGA = auto()
    LES = auto()


class KEpsilonModel(Enum):
    STANDARD = auto()
    RNG = auto()
    REALIZABLE = auto()


class NearWallTreatment(Enum):
    STANDARD_WALL_FUNCTIONS = auto()
    ENHANCED_WALL_TREATMENT = auto()


class KOmegaModel(Enum):
    SST = auto()


class TurbulenceModelDialog(QDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_TurbulenceDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()
        self._ui.kEpsilonModel.installEventFilter(self)

        self._ui.laminar.setChecked(True)
        self._ui.standard.setChecked(True)

    def _connectSignalsSlots(self):
        self._ui.modelRadioGroup.idToggled.connect(self._modelChanged)
        self._ui.kEpsilonRadioGroup.idToggled.connect(self._kEpsilonModelChanged)

    def _modelChanged(self, id_, checked):
        if checked:
            self._ui.kEpsilonModel.setVisible(self._ui.kEpsilon.isChecked())
            self._ui.kOmegaModel.setVisible(self._ui.kOmega.isChecked())

            QTimer.singleShot(0, lambda: self.adjustSize())

    def _kEpsilonModelChanged(self, id_, checked):
        if checked:
            self._ui.nearWallTreatment.setVisible(self._ui.realizable.isChecked())

            # QTimer.singleShot(0, lambda: self.adjustSize())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            QTimer.singleShot(0, lambda: self.adjustSize())

        return False
