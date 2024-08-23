#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from PySide6.QtCore import Qt

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.material_db import MaterialDB, Specification, Phase, MaterialType
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
from baramFlow.view.widgets.number_input_dialog import PolynomialDialog
from .material_dialog_ui import Ui_MaterialDialog


class MaterialDialog(ResizableDialog):
    def __init__(self, parent, mid: str):
        super().__init__(parent)
        self._ui = Ui_MaterialDialog()
        self._ui.setupUi(self)

        self._mid: str = mid
        self._xpath = MaterialDB.getXPath(mid)
        self._name = None
        self._type = MaterialDB.getType(self._mid)
        db = coredb.CoreDB()
        self._phase = Phase(db.getValue(self._xpath + '/phase'))
        self._polynomialDensity = None
        self._polynomialSpecificHeat = None
        self._polynomialViscosity = None
        self._polynomialThermalConductivity = None
        self._polynomialDialog = None

        layout = self._ui.properties.layout()
        layout.setRowVisible(self._ui.molecularWeight, self._phase != Phase.SOLID)
        layout.setRowVisible(self._ui.absorptionCoefficient, self._phase == Phase.GAS)
        layout.setRowVisible(self._ui.saturationPressure, self._phase == Phase.LIQUID)
        layout.setRowVisible(self._ui.emissivity, self._phase == Phase.SOLID)

        if self._phase != Phase.GAS:
            layout = self._ui.viscosityGroup.layout()
            layout.removeRow(self._ui.sutherlandCoefficient)
            layout.removeRow(self._ui.sutherlandTemperature)

        self._ui.viscosityGroup.setVisible(
            self._phase != Phase.SOLID and ModelsDB.getTurbulenceModel() != TurbulenceModel.INVISCID)

        self._connectSignalsSlots()
        self._load()

    def _load(self):
        self._name = MaterialDB.getName(self._mid)
        self._ui.name.setText(self._name)
        db = coredb.CoreDB()

        specXPath = (MaterialDB.getXPath(db.getValue(self._xpath + '/specie/mixture'))
                     if self._type == MaterialType.SPECIE else self._xpath)

        viscositySpecification = None
        if ModelsDB.isEnergyModelOn():
            densitySpecification = Specification(db.getValue(specXPath + '/density/specification'))

            specification = Specification(db.getValue(specXPath + '/specificHeat/specification'))
            self._setupSpecificHeatSpecification(specification)
            self._ui.constantSpecificHeat.setText(db.getValue(self._xpath + '/specificHeat/constant'))
            self._specificHeatTypeChanged()

            if self._phase != Phase.SOLID:
                viscositySpecification = Specification(db.getValue(specXPath + '/viscosity/specification'))

            specification = (Specification(db.getValue(self._xpath + '/thermalConductivity/specification'))
                             if self._type == MaterialType.NONMIXTURE else viscositySpecification)
            self._setupThermalConductivitySpecification(specification)
            self._ui.constantThermalConductivity.setText(db.getValue(self._xpath + '/thermalConductivity/constant'))
            self._thermalConductivityTypeChanged()

            if self._phase == Phase.SOLID:
                self._ui.emissivity.setText(db.getValue(self._xpath + '/emissivity'))
            else:
                self._ui.molecularWeight.setText(db.getValue(self._xpath + '/molecularWeight'))
                if self._phase == Phase.GAS:
                    self._ui.absorptionCoefficient.setText(db.getValue(self._xpath + '/absorptionCoefficient'))
                elif self._phase == Phase.LIQUID:
                    self._ui.saturationPressure.setText(db.getValue(self._xpath + '/saturationPressure'))
        else:
            densitySpecification = Specification.CONSTANT
            viscositySpecification = Specification.CONSTANT

            self._ui.densityType.setEnabled(False)
            self._ui.specificHeat.hide()
            self._ui.viscosityType.setEnabled(False)
            self._ui.thermalConductivity.hide()
            self._ui.properties.hide()

        self._setupDensitySpecification(densitySpecification)
        self._ui.constantDensity.setText(db.getValue(self._xpath + '/density/constant'))
        if self._phase == Phase.GAS:
            self._ui.criticalTemperature.setText(
                db.getValue(self._xpath + '/density/pengRobinsonParameters/criticalTemperature'))
            self._ui.criticalPressure.setText(
                db.getValue(self._xpath + '/density/pengRobinsonParameters/criticalPressure'))
            self._ui.criticalSpecificVolume.setText(
                db.getValue(self._xpath + '/density/pengRobinsonParameters/criticalSpecificVolume'))
            self._ui.acentricFactor.setText(
                db.getValue(self._xpath + '/density/pengRobinsonParameters/acentricFactor'))
        self._densityTypeChanged()

        if self._phase != Phase.SOLID:
            self._setupViscositySpecification(viscositySpecification)
            self._ui.constantViscosity.setText(db.getValue(self._xpath + '/viscosity/constant'))
            if self._phase == Phase.GAS:
                self._ui.sutherlandCoefficient.setText(
                    db.getValue(self._xpath + '/viscosity/sutherland/coefficient'))
                self._ui.sutherlandTemperature.setText(
                    db.getValue(self._xpath + '/viscosity/sutherland/temperature'))
            self._viscosityTypeChanged()

        self._polynomialDensity = None
        self._polynomialSpecificHeat = None
        self._polynomialViscosity = None
        self._polynomialThermalConductivity = None
        self._polynomialDialog = None

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name != self._name and MaterialDB.isMaterialExists(name):
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr(f'Material name "{name}" is already exists.'))
            return

        db = coredb.CoreDB()
        writer = CoreDBWriter()

        writer.append(self._xpath + '/name', name, self.tr('Name'))

        specification = self._ui.densityType.currentData()
        writer.append(self._xpath + '/density/specification', specification.value, None)
        if specification == Specification.CONSTANT:
            writer.append(self._xpath + '/density/constant', self._ui.constantDensity.text(), self.tr('Density Value'))
        elif specification == Specification.POLYNOMIAL:
            if self._polynomialDensity:
                writer.append(self._xpath + '/density/polynomial',
                              self._polynomialDensity, self.tr('Density Polynomial'))
            elif db.getValue(self._xpath + '/density/polynomial') == '':
                await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Edit Density Polynomial.'))
                return
        elif specification == Specification.REAL_GAS_PENG_ROBINSON:
            writer.append(self._xpath + '/density/constant', self._ui.constantDensity.text(), self.tr('Density Value'))
            writer.append(self._xpath + '/density/pengRobinsonParameters/criticalTemperature',
                          self._ui.criticalTemperature.text(), self.tr('Critical Temperature'))
            writer.append(self._xpath + '/density/pengRobinsonParameters/criticalPressure',
                          self._ui.criticalPressure.text(), self.tr('Critical Pressure'))
            writer.append(self._xpath + '/density/pengRobinsonParameters/criticalSpecificVolume',
                          self._ui.criticalSpecificVolume.text(), self.tr('Critical Specific Volume'))
            writer.append(self._xpath + '/density/pengRobinsonParameters/acentricFactor',
                          self._ui.acentricFactor.text(), self.tr('Acentric Factor'))

        viscositySpecification = None
        if self._phase != Phase.SOLID:
            viscositySpecification = self._ui.viscosityType.currentData()
            writer.append(self._xpath + '/viscosity/specification', viscositySpecification.value, None)
            if viscositySpecification == Specification.CONSTANT:
                writer.append(self._xpath + '/viscosity/constant',
                              self._ui.constantViscosity.text(), self.tr('Viscosity Value'))
            elif viscositySpecification == Specification.SUTHERLAND:
                writer.append(self._xpath + '/viscosity/sutherland/coefficient',
                              self._ui.sutherlandCoefficient.text(), self.tr('Sutherland Coefficient'))
                writer.append(self._xpath + '/viscosity/sutherland/temperature',
                              self._ui.sutherlandTemperature.text(), self.tr('Sutherland Temperature'))
            elif viscositySpecification == Specification.POLYNOMIAL:
                if self._polynomialViscosity:
                    writer.append(self._xpath + '/viscosity/polynomial',
                                  self._polynomialViscosity, self.tr('Viscosity Polynomial'))
                elif db.getValue(self._xpath + '/viscosity/polynomial') == '':
                    await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                        self.tr('Edit Viscosity Polynomial.'))
                    return

        if ModelsDB.isEnergyModelOn():
            specification = self._ui.specificHeatType.currentData()
            writer.append(self._xpath + '/specificHeat/specification', specification.value, None)
            if specification == Specification.CONSTANT:
                writer.append(self._xpath + '/specificHeat/constant',
                              self._ui.constantSpecificHeat.text(), self.tr('Specific Heat Value'))
            elif specification == Specification.POLYNOMIAL:
                if self._polynomialSpecificHeat:
                    writer.append(self._xpath + '/specificHeat/polynomial',
                                  self._polynomialSpecificHeat, self.tr('Specific Heat Polynomial'))
                elif db.getValue(self._xpath + '/specificHeat/polynomial') == '':
                    await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                        self.tr('Edit Specific Heat Polynomial.'))
                    return

            if viscositySpecification != Specification.SUTHERLAND:
                specification = self._ui.thermalConductivityType.currentData()
                writer.append(self._xpath + '/thermalConductivity/specification', specification.value, None)
                if specification == Specification.CONSTANT:
                    writer.append(self._xpath + '/thermalConductivity/constant',
                                  self._ui.constantThermalConductivity.text(), self.tr('Thermal Conductivity Value'))
                elif specification == Specification.POLYNOMIAL:
                    if self._polynomialThermalConductivity:
                        writer.append(self._xpath + '/thermalConductivity/polynomial',
                                      self._polynomialThermalConductivity, self.tr('Thermal Conductivity Polynomial'))
                    elif db.getValue(self._xpath + '/thermalConductivity/polynomial') == '':
                        await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                            self.tr('Edit Thermal Conductivity Polynomial.'))
                        return

            if self._phase == Phase.SOLID:
                writer.append(self._xpath + '/emissivity', self._ui.emissivity.text(), self.tr('Emissivity'))
            else:
                writer.append(self._xpath + '/molecularWeight',
                              self._ui.molecularWeight.text(), self.tr('Molecular Weight'))
                if self._phase == Phase.GAS:
                    writer.append(self._xpath + '/absorptionCoefficient',
                                  self._ui.absorptionCoefficient.text(), self.tr('Absorption Coefficient'))
                elif self._phase == Phase.LIQUID:
                    writer.append(self._xpath + '/saturationPressure',
                                  self._ui.saturationPressure.text(), self.tr('Saturation Pressure'))

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr('Input Error'), writer.firstError().toMessage())
        else:
            super().accept()

    def _setupDensitySpecification(self, spec):
        if self._type == MaterialType.SPECIE:
            self._setupSpecificationCombo(self._ui.densityType, [spec])
            self._ui.densityType.setEnabled(False)
        elif self._phase == Phase.GAS:
            self._setupSpecificationCombo(
                self._ui.densityType, [
                    Specification.CONSTANT,
                    Specification.PERFECT_GAS,
                    Specification.POLYNOMIAL
                ]
            )
        else:
            self._setupSpecificationCombo(
                self._ui.densityType, [
                    Specification.CONSTANT,
                ]
            )
            self._ui.densityType.setCurrentText(spec.value)

    def _setupSpecificHeatSpecification(self, spec):
        if self._type == MaterialType.SPECIE:
            self._setupSpecificationCombo(self._ui.specificHeatType, [spec])
            self._ui.specificHeatType.setEnabled(False)
        else:
            self._setupSpecificationCombo(
                self._ui.specificHeatType, [
                    Specification.CONSTANT,
                    Specification.POLYNOMIAL
                ]
            )
            self._ui.specificHeatType.setCurrentText(spec.value)

    def _setupViscositySpecification(self, spec):
        if self._type == MaterialType.SPECIE:
            self._setupSpecificationCombo(self._ui.viscosityType, [spec])
            self._ui.viscosityType.setEnabled(False)
        elif self._phase == Phase.GAS:
            self._setupSpecificationCombo(
                self._ui.viscosityType, [
                    Specification.CONSTANT,
                    Specification.SUTHERLAND,
                    Specification.POLYNOMIAL
                ]
            )
        elif self._phase == Phase.LIQUID:
            self._setupSpecificationCombo(
                self._ui.viscosityType, [
                    Specification.CONSTANT,
                    Specification.POLYNOMIAL
                ]
            )
            self._ui.viscosityType.setCurrentText(spec.value)

    def _setupThermalConductivitySpecification(self, spec):
        if self._type == MaterialType.SPECIE:
            self._setupSpecificationCombo(self._ui.thermalConductivityType, [spec])
            self._ui.thermalConductivityType.setEnabled(False)
        else:
            self._setupSpecificationCombo(
                self._ui.thermalConductivityType, [
                    Specification.CONSTANT,
                    Specification.POLYNOMIAL
                ]
            )
            self._ui.thermalConductivityType.setCurrentText(spec.value)

    def _setupSpecificationCombo(self, combo, types):
        for t in types:
            combo.addItem(MaterialDB.specificationToText(t), t)

    def _connectSignalsSlots(self):
        self._ui.densityType.currentTextChanged.connect(self._densityTypeChanged)
        self._ui.specificHeatType.currentTextChanged.connect(self._specificHeatTypeChanged)
        self._ui.viscosityType.currentTextChanged.connect(self._viscosityTypeChanged)
        self._ui.thermalConductivityType.currentTextChanged.connect(self._thermalConductivityTypeChanged)
        self._ui.densityEdit.clicked.connect(self._editDensity)
        self._ui.specificHeatEdit.clicked.connect(self._editSpecificHeat)
        self._ui.viscosityEdit.clicked.connect(self._editViscosity)
        self._ui.thermalConductivityEdit.clicked.connect(self._editThermalConductivity)
        self._ui.ok.clicked.connect(self._accept)

    def _densityTypeChanged(self):
        specification = self._ui.densityType.currentData(Qt.UserRole)
        self._ui.densityEdit.setEnabled(specification == Specification.POLYNOMIAL)
        self._ui.constantDensity.setEnabled(specification == Specification.CONSTANT)
        self._ui.pengRobinsonParameters.setVisible(specification == Specification.REAL_GAS_PENG_ROBINSON)

    def _specificHeatTypeChanged(self):
        specification = self._ui.specificHeatType.currentData(Qt.UserRole)
        self._ui.specificHeatEdit.setEnabled(specification == Specification.POLYNOMIAL)
        self._ui.constantSpecificHeat.setEnabled(specification == Specification.CONSTANT)

    def _viscosityTypeChanged(self):
        specification = self._ui.viscosityType.currentData(Qt.UserRole)
        self._ui.viscosityEdit.setEnabled(specification == Specification.POLYNOMIAL)
        self._ui.constantViscosity.setEnabled(specification == Specification.CONSTANT)
        if self._phase == Phase.GAS:
            isSpecSutherland = specification == Specification.SUTHERLAND
            self._ui.sutherlandCoefficient.setEnabled(isSpecSutherland)
            self._ui.sutherlandTemperature.setEnabled(isSpecSutherland)
            self._ui.thermalConductivity.setEnabled(not isSpecSutherland)

    def _thermalConductivityTypeChanged(self):
        specification = self._ui.thermalConductivityType.currentData(Qt.UserRole)
        self._ui.thermalConductivityEdit.setEnabled(specification == Specification.POLYNOMIAL)
        self._ui.constantThermalConductivity.setEnabled(specification == Specification.CONSTANT)

    def _editDensity(self):
        db = coredb.CoreDB()
        if self._polynomialDensity is None:
            self._polynomialDensity = db.getValue(self._xpath + '/density/polynomial')

        self._dialog = PolynomialDialog(self, self.tr('Polynomial Density'), self._polynomialDensity)
        self._dialog.accepted.connect(self._polynomialDensityAccepted)
        self._dialog.open()

    def _editSpecificHeat(self):
        db = coredb.CoreDB()
        if self._polynomialSpecificHeat is None:
            self._polynomialSpecificHeat = db.getValue(self._xpath + '/specificHeat/polynomial')

        self._dialog = PolynomialDialog(self, self.tr('Polynomial Specific Heat'), self._polynomialSpecificHeat)
        self._dialog.accepted.connect(self._polynomialSpeicificHeatAccepted)
        self._dialog.open()

    def _editViscosity(self):
        db = coredb.CoreDB()
        if self._polynomialViscosity is None:
            self._polynomialViscosity = db.getValue(self._xpath + '/viscosity/polynomial')

        self._dialog = PolynomialDialog(self, self.tr('Polynomial Viscosity'), self._polynomialViscosity)
        self._dialog.accepted.connect(self._polynomialViscosityAccepted)
        self._dialog.open()

    def _editThermalConductivity(self):
        db = coredb.CoreDB()
        if self._polynomialThermalConductivity is None:
            self._polynomialThermalConductivity = db.getValue(self._xpath + '/thermalConductivity/polynomial')

        self._dialog = PolynomialDialog(self, self.tr('Polynomial Thermal Conductivity'),
                                        self._polynomialThermalConductivity)
        self._dialog.accepted.connect(self._polynomialThermalConductivityAccepted)
        self._dialog.open()

    def _polynomialDensityAccepted(self):
        self._polynomialDensity = self._dialog.getValues()

    def _polynomialSpeicificHeatAccepted(self):
        self._polynomialSpecificHeat = self._dialog.getValues()

    def _polynomialViscosityAccepted(self):
        self._polynomialViscosity = self._dialog.getValues()

    def _polynomialThermalConductivityAccepted(self):
        self._polynomialThermalConductivity = self._dialog.getValues()
