#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from coredb import coredb
from coredb.boundary_db import SpalartAllmarasSpecification
from .turbulence_spalart_allmaras_widget_ui import Ui_turbulenceSpalartAllmarasWidget


class TurbulenceSpalartAllmarasWidget(QWidget):
    RELATIVE_XPATH = '/turbulence/spalartAllmaras'

    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_turbulenceSpalartAllmarasWidget()
        self._ui.setupUi(self)

        self._specificationMethods = {
            SpalartAllmarasSpecification.MODIFIED_TURBULENT_VISCOSITY.value: self.tr("Modified Turbulent Viscosity"),
            SpalartAllmarasSpecification.TURBULENT_VISCOSITY_RATIO.value: self.tr("Turbulent Viscosity Ratio"),
        }
        self._setupSpecificationMethodCombo()

        self._db = coredb.CoreDB()
        self._xpath = xpath

        self._connectSignalsSlots()

    def on(self):
        return True

    def load(self):
        xpath = self._xpath + self.RELATIVE_XPATH

        self._ui.specificationMethod.setCurrentText(
            self._specificationMethods[self._db.getValue(xpath + '/specification')])
        self._ui.modifiedTurbulentViscosity.setText(self._db.getValue(xpath + '/modifiedTurbulentViscosity'))
        self._ui.turbulentViscosityRatio.setText(self._db.getValue(xpath + '/turbulentViscosityRatio'))
        self._specificationMethodChanged()

    def appendToWriter(self, writer):
        xpath = self._xpath + self.RELATIVE_XPATH

        specification = self._ui.specificationMethod.currentData()
        writer.append(xpath + '/specification', specification, None)
        if specification == SpalartAllmarasSpecification.MODIFIED_TURBULENT_VISCOSITY.value:
            writer.append(xpath + '/modifiedTurbulentViscosity', self._ui.modifiedTurbulentViscosity.text(),
                          self.tr("Modified Turbulent Viscosity"))
        elif specification == SpalartAllmarasSpecification.TURBULENT_VISCOSITY_RATIO.value:
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
        self._ui.modifiedTurbulentViscosityWidget.setVisible(
            specification == SpalartAllmarasSpecification.MODIFIED_TURBULENT_VISCOSITY.value)
        self._ui.turbulentViscosityRatioWidget.setVisible(
            specification == SpalartAllmarasSpecification.TURBULENT_VISCOSITY_RATIO.value)
