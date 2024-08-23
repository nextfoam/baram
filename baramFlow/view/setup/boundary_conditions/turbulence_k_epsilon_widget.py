#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import KEpsilonSpecification
from .turbulence_k_epsilon_widget_ui import Ui_turbulenceKEpsilonWidget


class TurbulenceKEpsilonWidget(QWidget):
    RELATIVE_XPATH = '/turbulence/k-epsilon'

    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_turbulenceKEpsilonWidget()
        self._ui.setupUi(self)

        self._specificationMethods = {
            KEpsilonSpecification.K_AND_EPSILON.value: self.tr("K and Epsilon"),
            KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value: self.tr("Intensity and Viscosity Ratio"),
        }
        self._setupSpecificationMethodCombo()

        self._xpath = xpath

        self._connectSignalsSlots()

        self._specificationMethodChanged()

    def on(self):
        return True

    def load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._ui.specificationMethod.setCurrentText(
            self._specificationMethods[db.getValue(xpath + '/specification')])
        self._ui.turbulentKineticEnergy.setText(db.getValue(xpath + '/turbulentKineticEnergy'))
        self._ui.turbuelnetDissipationRate.setText(db.getValue(xpath + '/turbulentDissipationRate'))
        self._ui.turbulentIntensity.setText(db.getValue(xpath + '/turbulentIntensity'))
        self._ui.turbulentViscosityRatio.setText(db.getValue(xpath + '/turbulentViscosityRatio'))
        self._specificationMethodChanged()

    def appendToWriter(self, writer):
        xpath = self._xpath + self.RELATIVE_XPATH

        specification = self._ui.specificationMethod.currentData()
        writer.append(xpath + '/specification', specification, None)
        if specification == KEpsilonSpecification.K_AND_EPSILON.value:
            writer.append(xpath + '/turbulentKineticEnergy', self._ui.turbulentKineticEnergy.text(),
                          self.tr('Turbulent Kinetic Energy'))
            writer.append(xpath + '/turbulentDissipationRate', self._ui.turbuelnetDissipationRate.text(),
                          self.tr("Turbulent Dissipation Rate"))
        elif specification == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            writer.append(xpath + '/turbulentIntensity', self._ui.turbulentIntensity.text(),
                          self.tr("Turbulent Intensity"))
            writer.append(xpath + '/turbulentViscosityRatio', self._ui.turbulentViscosityRatio.text(),
                          self.tr("Turbulent Viscosity Ratio"))

        return True

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._specificationMethodChanged)

    def _setupSpecificationMethodCombo(self):
        for value, text in self._specificationMethods.items():
            self._ui.specificationMethod.addItem(text, value)

    def _specificationMethodChanged(self):
        specification = self._ui.specificationMethod.currentData()
        self._ui.kAndEpsilon.setVisible(
            specification == KEpsilonSpecification.K_AND_EPSILON.value)
        self._ui.intensityAndViscocityRatio.setVisible(
            specification == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value)
