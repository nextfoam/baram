#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QWidget

from .turbulence_k_omega_widget_ui import Ui_turbulenceKOmegaWidget


class SpecificationMethod(Enum):
    K_AND_OMEGA                   = "kAndEpsilon"
    INTENSITY_AND_VISCOCITY_RATIO = "intensityAndViscosityRatio"


class TurbulenceKOmegaWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self._ui = Ui_turbulenceKOmegaWidget()

        self._parent = parent

        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def load(self, db, xpath):
        path = xpath + '/turbulence/k-omega'

        self._setupSpecificationMethodCombo(db.getValue(path + '/specification'))
        self._ui.turbulentKineticEnerge.setText(db.getValue(path + '/turbulentKineticEnergy'))
        self._ui.specificDissipationRate.setText(db.getValue(path + '/specificDissipationRate'))
        self._ui.turbulentIntensity.setText(db.getValue(path + '/turbulentIntensity'))
        self._ui.turbulentViscosityRatio.setText(db.getValue(path + '/turbulentViscosityRatio'))

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._specificationMethodChanged)

    def _setupSpecificationMethodCombo(self, specification):
        self._addSpecificationMethodComboItem(specification, SpecificationMethod.K_AND_OMEGA,
                                              self.tr("K and Omega"))
        self._addSpecificationMethodComboItem(specification, SpecificationMethod.INTENSITY_AND_VISCOCITY_RATIO,
                                              self.tr("Intensity and Viscosity Ratio"))


    def _specificationMethodChanged(self):
        method = self._ui.specificationMethod.currentData(Qt.UserRole)
        self._ui.kAndOmega.setVisible(method == SpecificationMethod.K_AND_OMEGA)
        self._ui.intensityAndViscocityRatio.setVisible(method == SpecificationMethod.INTENSITY_AND_VISCOCITY_RATIO)

        QTimer.singleShot(0, lambda: self._parent.adjustSize())

    def _addSpecificationMethodComboItem(self, current, method, text):
        self._ui.specificationMethod.addItem(text, method)
        if current == method.value:
            self._ui.specificationMethod.setCurrentIndex(self._ui.specificationMethod.count() - 1)
