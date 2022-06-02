#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from .turbulence_k_omega_widget_ui import Ui_turbulenceKOmegaWidget


class SpecificationMethod(Enum):
    K_AND_OMEGA                   = "kAndOmega"
    INTENSITY_AND_VISCOSITY_RATIO = "intensityAndViscosityRatio"


class TurbulenceKOmegaWidget(QWidget):
    RELATIVE_PATH = '/turbulence/k-omega'

    def __init__(self, parent):
        super().__init__()
        self._ui = Ui_turbulenceKOmegaWidget()

        self._parent = parent

        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def load(self, db, xpath):
        path = xpath + self.RELATIVE_PATH

        self._setupSpecificationMethodCombo(db.getValue(path + '/specification'))
        self._ui.turbulentKineticEnergy.setText(db.getValue(path + '/turbulentKineticEnergy'))
        self._ui.specificDissipationRate.setText(db.getValue(path + '/specificDissipationRate'))
        self._ui.turbulentIntensity.setText(db.getValue(path + '/turbulentIntensity'))
        self._ui.turbulentViscosityRatio.setText(db.getValue(path + '/turbulentViscosityRatio'))

    def appendToWriter(self, writer, xpath):
        path = xpath + self.RELATIVE_PATH

        specification = self._ui.specificationMethod.currentData()
        writer.append(path + '/specification', specification.value, None)

        if specification == SpecificationMethod.K_AND_OMEGA:
            writer.append(path + '/turbulentKineticEnergy', self._ui.turbulentKineticEnergy.text(),
                          self.tr("Turbulent Kinetic Energy"))
            writer.append(path + '/specificDissipationRate', self._ui.specificDissipationRate.text(),
                          self.tr("Specific Dissipation Rate"))
        elif specification == SpecificationMethod.INTENSITY_AND_VISCOSITY_RATIO:
            writer.append(path + '/turbulentIntensity', self._ui.turbulentIntensity.text(),
                          self.tr("Turbulent Intensity"))
            writer.append(path + '/turbulentViscosityRatio', self._ui.turbulentViscosityRatio.text(),
                          self.tr("Turbulent Viscosity Ratio"))

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._specificationMethodChanged)

    def _setupSpecificationMethodCombo(self, specification):
        self._addSpecificationMethodComboItem(specification, SpecificationMethod.K_AND_OMEGA,
                                              self.tr("K and Omega"))
        self._addSpecificationMethodComboItem(specification, SpecificationMethod.INTENSITY_AND_VISCOSITY_RATIO,
                                              self.tr("Intensity and Viscosity Ratio"))


    def _specificationMethodChanged(self):
        method = self._ui.specificationMethod.currentData(Qt.UserRole)
        self._ui.kAndOmega.setVisible(method == SpecificationMethod.K_AND_OMEGA)
        self._ui.intensityAndViscocityRatio.setVisible(method == SpecificationMethod.INTENSITY_AND_VISCOSITY_RATIO)

    def _addSpecificationMethodComboItem(self, current, method, text):
        self._ui.specificationMethod.addItem(text, method)
        if current == method.value:
            self._ui.specificationMethod.setCurrentIndex(self._ui.specificationMethod.count() - 1)
