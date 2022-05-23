#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .numerical_conditions_page_ui import Ui_NumericalConditionsPage
from .advanced_dialog import AdvancedDialog


class NumericalConditionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_NumericalConditionsPage()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def load(self):
        self._setTime()
        pass

    def save(self):
        pass

    def _connectSignalsSlots(self):
        self._ui.advanced.clicked.connect(self._advancedSetup)
        pass

    def _setTime(self):
        timeIsTransient = False
        self._ui.discretizationSchemeTime.setEnabled(timeIsTransient)
        self._ui.discretizationSchemeTime.addItem("")
        self._ui.discretizationSchemeTime.setCurrentText("")
        self._ui.underRelaxationFactorPressureFinal.setEnabled(timeIsTransient)
        self._ui.underRelaxationFactorMomentumFinal.setEnabled(timeIsTransient)
        self._ui.underRelaxationFactorEnergyFinal.setEnabled(timeIsTransient)
        self._ui.underRelaxationFactorTurbulenceFinal.setEnabled(timeIsTransient)
        self._ui.maxIterationsPerTimeStep.setEnabled(timeIsTransient)
        self._ui.numberOfCorrectors.setEnabled(timeIsTransient)
        self._ui.relativePressure.setEnabled(timeIsTransient)
        self._ui.relativeMomentum.setEnabled(timeIsTransient)
        self._ui.relativeEnergy.setEnabled(timeIsTransient)
        self._ui.relativeTurbulence.setEnabled(timeIsTransient)

    def _advancedSetup(self):
        dialog = AdvancedDialog()
        dialog.exec()