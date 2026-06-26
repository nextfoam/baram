#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.numberical_condition.numberical_condition import NumericalAdvanced, NumericalLimits, EnergyEquation
from baramFlow.base.numberical_condition.numberical_condition import NumericalEquations, CollateralFields
from baramFlow.case_manager import CaseManager
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.services.numerical_condition.numberical_service import NumericalService
from .advanced_dialog_ui import Ui_AdvancedDialog


class AdvancedDialog(QDialog):
    RELATIVE_XPATH = '/advanced'

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_AdvancedDialog()
        self._ui.setupUi(self)

        self._xpath = NumericalDB.NUMERICAL_CONDITIONS_XPATH + self.RELATIVE_XPATH

        isDensityBased = GeneralDB.isDensityBased()
        isEnergeOn = ModelsDB.isEnergyModelOn()

        if not isEnergeOn:
            self._ui.equationEnergy.setEnabled(False)
            self._ui.includeViscousDissipationTerms.setEnabled(False)
            self._ui.includeKineticEnergyTerms.setEnabled(False)
            self._ui.includePressureWorkTerms.setEnabled(False)

        self._ui.equationUDS.setEnabled(UserDefinedScalarsDB.hasDefined())

        self._ui.collateralAge.setEnabled(not GeneralDB.isTimeTransient() and not isDensityBased)
        self._ui.collateralHeatTransferCoefficient.setEnabled(isEnergeOn)
        self._ui.collateralMachNumber.setEnabled(isEnergeOn and not isDensityBased)

        if CaseManager().isBatchRunning():
            self._ui.dialogContents.setEnabled(False)
            self._ui.ok.setEnabled(False)

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
        self._ui.equationEnergy.toggled.connect(self._equationEnergyToggled)
        self._ui.includeViscousDissipationTerms.toggled.connect(self._includeViscousDissipationTermsToggled)

    @qasync.asyncSlot()
    async def _accept(self):
        loaded = NumericalService.getConditions().advanced

        try:
            if ModelsDB.isEnergyModelOn():
                equationEnergy = EnergyEquation(
                    disabled=not self._ui.equationEnergy.isChecked(),
                    includeViscousDissipationTerms=self._ui.includeViscousDissipationTerms.isChecked(),
                    includeKineticEnergyTerms=self._ui.includeKineticEnergyTerms.isChecked(),
                    includePressureWorkTerms=self._ui.includePressureWorkTerms.isChecked())
            else:
                equationEnergy = loaded.equations.energy

            data = NumericalAdvanced(
                limits=NumericalLimits(
                    minimumStaticTemperature=self._ui.minimumStaticTemperature.pFloat(
                        self.tr("Minimum Static Temperature")),
                    maximumStaticTemperature=self._ui.maximumStaticTemperature.pFloat(
                        self.tr("Maximum Static Temperature")),
                    maximumViscosityRatio=self._ui.maximumViscosityRatio.pFloat(self.tr("Maximum Viscosity Ratio"))),
                equations=NumericalEquations(
                    flow=self._ui.equationFlow.isChecked(),
                    energy=equationEnergy,
                    UDS=self._ui.equationUDS.isChecked() if UserDefinedScalarsDB.hasDefined() else loaded.equations.UDS),
                collateralFields=CollateralFields(
                    age=self._ui.collateralAge.isChecked(),
                    heatTransferCoefficient=self._ui.collateralHeatTransferCoefficient.isChecked(),
                    machNumber=self._ui.collateralMachNumber.isChecked(),
                    q=self._ui.collateralQ.isChecked(),
                    totalPressure=self._ui.collateralTotalPressure.isChecked(),
                    vorticity=self._ui.collateralVorticity.isChecked(),
                    wallHeatFlux=self._ui.collateralWallHeatFlux.isChecked(),
                    wallShearStress=self._ui.collateralWallShearStress.isChecked(),
                    wallYPlus=self._ui.collateralWallYPlus.isChecked()))

            NumericalService.updateAdvanced(data)
            self.accept()
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

    def _load(self):
        data = NumericalService.getConditions().advanced

        equationEnergyOn = not data.equations.energy.disabled
        includeViscousDissipationTerms = data.equations.energy.includeViscousDissipationTerms

        self._ui.minimumStaticTemperature.setPFloat(data.limits.minimumStaticTemperature)
        self._ui.maximumStaticTemperature.setPFloat(data.limits.maximumStaticTemperature)
        self._ui.maximumViscosityRatio.setPFloat(data.limits.maximumViscosityRatio)

        self._ui.equationFlow.setChecked(data.equations.flow)
        self._ui.equationEnergy.setChecked(equationEnergyOn)
        self._ui.equationUDS.setChecked(data.equations.UDS)

        self._ui.includeViscousDissipationTerms.setChecked(includeViscousDissipationTerms)
        self._ui.includeKineticEnergyTerms.setChecked(data.equations.energy.includeKineticEnergyTerms)
        self._ui.includePressureWorkTerms.setChecked(data.equations.energy.includePressureWorkTerms)

        if not GeneralDB.isDensityBased():
            self._ui.energyTerms.setEnabled(equationEnergyOn)

            if includeViscousDissipationTerms:
                self._ui.includeKineticEnergyTerms.setEnabled(False)
                self._ui.includePressureWorkTerms.setEnabled(False)
        else:
            self._ui.equationEnergy.setEnabled(False)
            self._ui.energyTerms.setEnabled(False)

        self._ui.collateralAge.setChecked(data.collateralFields.age)
        self._ui.collateralHeatTransferCoefficient.setChecked(data.collateralFields.heatTransferCoefficient)
        self._ui.collateralMachNumber.setChecked(data.collateralFields.machNumber)
        self._ui.collateralQ.setChecked(data.collateralFields.q)
        self._ui.collateralTotalPressure.setChecked(data.collateralFields.totalPressure)
        self._ui.collateralVorticity.setChecked(data.collateralFields.vorticity)
        self._ui.collateralWallHeatFlux.setChecked(data.collateralFields.wallHeatFlux)
        self._ui.collateralWallShearStress.setChecked(data.collateralFields.wallShearStress)
        self._ui.collateralWallYPlus.setChecked(data.collateralFields.wallYPlus)

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
