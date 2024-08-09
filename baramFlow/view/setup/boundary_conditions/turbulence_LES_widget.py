#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import SubgridKineticEnergySpecificationMethod
from .turbulence_LES_widget_ui import Ui_TurbulenceLESWidget


class TurbulenceLESWidget(QWidget):
    RELATIVE_XPATH = '/turbulence/les'

    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_TurbulenceLESWidget()
        self._ui.setupUi(self)

        self._ui.specificationMethod.addEnumItems({
            SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_K:            self.tr('Subgrid-Scale K'),
            SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_INTENSITY:    self.tr('Subgrid-Scale Intensity')
        })

        self._xpath = xpath

        self._connectSignalsSlots()

    def on(self):
        return True

    def load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._ui.specificationMethod.setCurrentData(
            SubgridKineticEnergySpecificationMethod(db.getValue(xpath + '/specification')))
        self._ui.kineticEnergy.setText(db.getValue(xpath + '/subgridKineticEnergy'))
        self._ui.turbulentIntensity.setText(db.getValue(xpath + '/subgridTurbulentIntensity'))
        self._ui.turbulentViscosityRatio.setText(db.getValue(xpath + '/turbulentViscosityRatio'))

    def appendToWriter(self, writer):
        xpath = self._xpath + self.RELATIVE_XPATH

        specification = self._ui.specificationMethod.currentData()
        writer.append(xpath + '/specification', specification.value, None)
        if specification == SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_K:
            writer.append(xpath + '/subgridKineticEnergy', self._ui.kineticEnergy.text(),
                          self.tr('Subgrid Kinetic Energy'))
        elif specification == SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_INTENSITY:
            writer.append(xpath + '/subgridTurbulentIntensity', self._ui.turbulentIntensity.text(),
                          self.tr("Subgrid Turbulent Intensity"))

        writer.append(xpath + '/turbulentViscosityRatio', self._ui.turbulentViscosityRatio.text(),
                      self.tr("Turbulent Viscosity Ratio"))

        return True

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentDataChanged.connect(self._specificationMethodChanged)

    def _specificationMethodChanged(self, specification):
        self._ui.parametersLayout.setRowVisible(
            self._ui.kineticEnergy, specification == SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_K)
        self._ui.parametersLayout.setRowVisible(
            self._ui.turbulentIntensity,
            specification == SubgridKineticEnergySpecificationMethod.SUBGRID_SCALE_INTENSITY)
