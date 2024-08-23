#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter, boolToDBText
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.coredb.numerical_db import NumericalDB
from .advanced_dialog_ui import Ui_AdvancedDialog


class AdvancedDialog(QDialog):
    RELATIVE_XPATH = '/advanced'

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_AdvancedDialog()
        self._ui.setupUi(self)

        self._xpath = NumericalDB.NUMERICAL_CONDITIONS_XPATH + self.RELATIVE_XPATH

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
        self._ui.equationEnergy.toggled.connect(self._equationEnergyToggled)
        self._ui.includeViscousDissipationTerms.toggled.connect(self._includeViscousDissipationTermsToggled)

    @qasync.asyncSlot()
    async def _accept(self):
        writer = CoreDBWriter()
        writer.append(self._xpath + '/limits/minimumStaticTemperature', self._ui.minimumStaticTemperature.text(),
                      self.tr("Minimum Static Temperature"))
        writer.append(self._xpath + '/limits/maximumStaticTemperature', self._ui.maximumStaticTemperature.text(),
                      self.tr("Maximum Static Temperature"))
        writer.append(self._xpath + '/limits/maximumViscosityRatio', self._ui.maximumViscosityRatio.text(),
                      self.tr("Maximum Viscosity Ratio"))

        writer.append(self._xpath + '/equations/flow', boolToDBText(self._ui.equationFlow.isChecked()), None)
        if ModelsDB.isEnergyModelOn():
            writer.setAttribute(self._xpath + '/equations/energy', 'disabled',
                                boolToDBText(not self._ui.equationEnergy.isChecked()))
            writer.append(self._xpath + '/equations/energy/includeViscousDissipationTerms',
                          boolToDBText(self._ui.includeViscousDissipationTerms.isChecked()), None)
            writer.append(self._xpath + '/equations/energy/includeKineticEnergyTerms',
                          boolToDBText(self._ui.includeKineticEnergyTerms                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               .isChecked()), None)
            writer.append(self._xpath + '/equations/energy/includePressureWorkTerms',
                          boolToDBText(self._ui.includePressureWorkTerms.isChecked()), None)

        if UserDefinedScalarsDB.hasDefined():
            writer.append(self._xpath + '/equations/UDS', boolToDBText(self._ui.equationUDS.isChecked()), None)

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.accept()

    def _load(self):
        db = coredb.CoreDB()
        self._ui.minimumStaticTemperature.setText(db.getValue(self._xpath + '/limits/minimumStaticTemperature'))
        self._ui.maximumStaticTemperature.setText(db.getValue(self._xpath + '/limits/maximumStaticTemperature'))
        self._ui.maximumViscosityRatio.setText(db.getValue(self._xpath + '/limits/maximumViscosityRatio'))

        equationEnergyOn = db.getAttribute(self._xpath + '/equations/energy', 'disabled') == 'false'
        self._ui.equationFlow.setChecked(db.getBool(self._xpath + '/equations/flow'))
        self._ui.equationEnergy.setChecked(equationEnergyOn)
        self._ui.equationUDS.setChecked(db.getBool(self._xpath + '/equations/UDS'))

        includeViscousDissipationTerms = db.getBool(
            self._xpath + '/equations/energy/includeViscousDissipationTerms')
        self._ui.includeViscousDissipationTerms.setChecked(includeViscousDissipationTerms)
        self._ui.includeKineticEnergyTerms.setChecked(
            db.getBool(self._xpath + '/equations/energy/includeKineticEnergyTerms'))
        self._ui.includePressureWorkTerms.setChecked(
            db.getBool(self._xpath + '/equations/energy/includePressureWorkTerms'))

        if not GeneralDB.isDensityBased():
            self._ui.energyTerms.setEnabled(equationEnergyOn)

            if includeViscousDissipationTerms:
                self._ui.includeKineticEnergyTerms.setEnabled(False)
                self._ui.includePressureWorkTerms.setEnabled(False)
        else:
            self._ui.equationEnergy.setEnabled(False)
            self._ui.energyTerms.setEnabled(False)

    def _equationEnergyToggled(self, checked):
        self._ui.energyTerms.setEnabled(checked)

        if not checked:
            self._ui.includeViscousDissipationTerms.setChecked(False)
            self._ui.includeKineticEnergyTerms.setChecked(False)
            self._ui.includePressureWorkTerms.setChecked(False)

    def _includeViscousDissipationTermsToggled(self, checked):
        if checked:
            self._ui.includeKineticEnergyTerms.setChecked(True)
            self._ui.includePressureWorkTerms.setChecked(True)
            self._ui.includeKineticEnergyTerms.setEnabled(False)
            self._ui.includePressureWorkTerms.setEnabled(False)
        elif self._ui.equationEnergy.isChecked():
            self._ui.includeKineticEnergyTerms.setEnabled(True)
            self._ui.includePressureWorkTerms.setEnabled(True)
