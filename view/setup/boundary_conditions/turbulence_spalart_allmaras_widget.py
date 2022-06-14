#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from coredb import coredb
from .turbulence_spalart_allmaras_widget_ui import Ui_turbulenceSpalartAllmarasWidget
from .boundary_db import SpalartAllmarasSpecification


class TurbulenceSpalartAllmarasWidget(QWidget):
    RELATIVE_PATH = '/turbulence/spalartAllmaras'

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

    def load(self):
        path = self._xpath + self.RELATIVE_PATH

        self._ui.specificationMethod.setCurrentText(
            self._specificationMethods[self._db.getValue(path + '/specification')])
        self._ui.modifiedTurbulentViscosity.setText(self._db.getValue(path + '/modifiedTurbulentViscosity'))
        self._ui.turbulentViscosityRatio.setText(self._db.getValue(path + '/turbulentViscosityRatio'))
        self._specificationMethodChanged()

    def appendToWriter(self, writer):
        path = self._xpath + self.RELATIVE_PATH

        specification = self._ui.specificationMethod.currentData()
        writer.append(path + '/specification', specification, None)
        if specification == SpalartAllmarasSpecification.MODIFIED_TURBULENT_VISCOSITY.value:
            writer.append(path + '/modifiedTurbulentViscosity', self._ui.modifiedTurbulentViscosity.text(),
                          self.tr("Modified Turbulent Viscosity"))
        elif specification == SpalartAllmarasSpecification.TURBULENT_VISCOSITY_RATIO.value:
            writer.append(path + '/turbulentViscosityRatio', self._ui.turbulentViscosityRatio.text(),
                          self.tr("Turbulent Viscosity Ratio"))

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
