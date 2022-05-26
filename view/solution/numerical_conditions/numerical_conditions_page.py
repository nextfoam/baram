#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from coredb import coredb
from .numerical_conditions_page_ui import Ui_NumericalConditionsPage
from .advanced_dialog import AdvancedDialog


class NumericalConditionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_NumericalConditionsPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._connectSignalsSlots()
        self._load()

    def hideEvent(self, ev):
        if ev.spontaneous():
            return

    def _connectSignalsSlots(self):
        self._ui.advanced.clicked.connect(self._advancedSetup)
        pass

    def _load(self):
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