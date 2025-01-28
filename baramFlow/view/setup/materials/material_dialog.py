#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import Phase, MaterialType
from baramFlow.coredb.material_schema import Specification, ViscositySpecification, DensitySpecification
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.view.widgets.number_input_dialog import PolynomialDialog
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .material_dialog_ui import Ui_MaterialDialog
from .viscosity_carreau_dialog import ViscosityCarreauDialog
from .viscosity_cross_dialog import ViscosityCrossDialog
from .viscosity_herschel_bulkley_dialog import ViscosityHerschelBulkleyDialog
from .viscosity_non_newtonian_power_law_dialog import ViscosityNonNewtonianPowerLawDialog


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
        self._polynomialThermalConductivity = None
        self._polynomialDialog = None
        self._viscosities = None

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
            self._phase != Phase.SOLID and TurbulenceModelsDB.getModel() != TurbulenceModel.INVISCID)

        if self._phase != Phase.SOLID and TurbulenceModelsDB.getModel() == TurbulenceModel.INVISCID:
            self._ui.thermalConductivity.hide()

        self._connectSignalsSlots()
        self._load()

    def _load(self):
        self._name = MaterialDB.getName(self._mid)
        self._ui.name.setText(self._name)
        db = coredb.CoreDB()

        viscositySpecification = (
            None if self._phase == Phase.SOLID
            else ViscositySpecification(db.getValue(self._xpath + '/viscosity/specification')))

        if ModelsDB.isEnergyModelOn():
            densitySpecification = DensitySpecification(db.getValue(self._xpath + '/density/specification'))

            specification = Specification(db.getValue(self._xpath + '/specificHeat/specification'))
            self._setupSpecificHeatSpecification(specification)
            self._ui.constantSpecificHeat.setText(db.getValue(self._xpath + '/specificHeat/constant'))

            if viscositySpecification == ViscositySpecification.SUTHERLAND and self._type == MaterialType.SPECIE:
                self._ui.thermalConductivity.hide()
            else:
                specification = Specification(db.getValue(self._xpath + '/thermalConductivity/specification'))
                self._setupThermalConductivitySpecification(specification)
                self._ui.constantThermalConductivity.setText(
                    db.getValue(self._xpath + '/thermalConductivity/constant'))

            if self._phase == Phase.SOLID:
                self._ui.emissivity.setText(db.getValue(self._xpath + '/emissivity'))
            else:
                self._ui.molecularWeight.setText(db.getValue(self._xpath + '/molecularWeight'))
                if self._phase == Phase.GAS:
                    self._ui.absorptionCoefficient.setText(db.getValue(self._xpath + '/absorptionCoefficient'))
                elif self._phase == Phase.LIQUID:
                    self._ui.saturationPressure.setText(db.getValue(self._xpath + '/saturationPressure'))
        else:
            densitySpecification = DensitySpecification.CONSTANT
            if TurbulenceModelsDB.getModel() != TurbulenceModel.LAMINAR:
                viscositySpecification = ViscositySpecification.CONSTANT
                self._ui.viscosityType.setEnabled(False)

            self._ui.densityType.setEnabled(False)
            self._ui.specificHeat.hide()
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

        if self._phase != Phase.SOLID:
            self._setupViscositySpecification(viscositySpecification)
            self._ui.constantViscosity.setText(db.getValue(self._xpath + '/viscosity/constant'))
            if self._phase == Phase.GAS:
                self._ui.sutherlandCoefficient.setText(
                    db.getValue(self._xpath + '/viscosity/sutherland/coefficient'))
                self._ui.sutherlandTemperature.setText(
                    db.getValue(self._xpath + '/viscosity/sutherland/temperature'))

        self._polynomialDensity = None
        self._polynomialSpecificHeat = None
        self._viscosities = {
            ViscositySpecification.POLYNOMIAL: None,
            ViscositySpecification.CROSS_POWER_LAW: None,
            ViscositySpecification.HERSCHEL_BULKLEY: None,
            ViscositySpecification.BIRD_CARREAU: None,
            ViscositySpecification.POWER_LAW: None
        }
        self._polynomialThermalConductivity = None
        self._polynomialDialog = None

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name != self._name and MaterialDB.isMaterialExists(name):
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr(f'Material name "{name}" is already exists.'))
            return

        try:
            with coredb.CoreDB() as db:
                db.setValue(self._xpath + '/name', name, self.tr('Name'))

                specification = self._ui.densityType.currentData()
                db.setValue(self._xpath + '/density/specification', specification.value, None)
                if specification == DensitySpecification.CONSTANT:
                    db.setValue(self._xpath + '/density/constant', self._ui.constantDensity.text(),
                                self.tr('Density Value'))
                elif specification == DensitySpecification.POLYNOMIAL:
                    if self._polynomialDensity:
                        db.setValue(self._xpath + '/density/polynomial',
                                      self._polynomialDensity, self.tr('Density Polynomial'))
                    elif db.getValue(self._xpath + '/density/polynomial') == '':
                        await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                            self.tr('Edit Density Polynomial.'))
                        return
                elif specification == DensitySpecification.REAL_GAS_PENG_ROBINSON:
                    db.setValue(self._xpath + '/density/constant', self._ui.constantDensity.text(),
                                self.tr('Density Value'))
                    db.setValue(self._xpath + '/density/pengRobinsonParameters/criticalTemperature',
                                  self._ui.criticalTemperature.text(), self.tr('Critical Temperature'))
                    db.setValue(self._xpath + '/density/pengRobinsonParameters/criticalPressure',
                                  self._ui.criticalPressure.text(), self.tr('Critical Pressure'))
                    db.setValue(self._xpath + '/density/pengRobinsonParameters/criticalSpecificVolume',
                                  self._ui.criticalSpecificVolume.text(), self.tr('Critical Specific Volume'))
                    db.setValue(self._xpath + '/density/pengRobinsonParameters/acentricFactor',
                                  self._ui.acentricFactor.text(), self.tr('Acentric Factor'))

                viscositySpecification = None
                if self._phase != Phase.SOLID:
                    viscositySpecification = self._ui.viscosityType.currentData()
                    db.setValue(self._xpath + '/viscosity/specification', viscositySpecification.value, None)
                    if viscositySpecification == ViscositySpecification.CONSTANT:
                        db.setValue(self._xpath + '/viscosity/constant',
                                      self._ui.constantViscosity.text(), self.tr('Viscosity Value'))
                    elif viscositySpecification == ViscositySpecification.SUTHERLAND:
                        db.setValue(self._xpath + '/viscosity/sutherland/coefficient',
                                      self._ui.sutherlandCoefficient.text(), self.tr('Sutherland Coefficient'))
                        db.setValue(self._xpath + '/viscosity/sutherland/temperature',
                                      self._ui.sutherlandTemperature.text(), self.tr('Sutherland Temperature'))
                    else:
                        viscosity = self._viscosities[viscositySpecification]
                        if viscositySpecification == ViscositySpecification.POLYNOMIAL:
                            if viscosity:
                                db.setValue(self._xpath + '/viscosity/polynomial', viscosity,
                                            self.tr('Viscosity Polynomial'))
                            elif db.getValue(self._xpath + '/viscosity/polynomial') == '':
                                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                                    self.tr('Edit Viscosity Polynomial.'))
                                return
                        elif viscosity:
                            properties = []
                            if viscositySpecification == ViscositySpecification.CROSS_POWER_LAW:
                                properties.append(('/viscosity/cross/zeroShearViscosity', viscosity.zeroShearViscosity))
                                properties.append(
                                    ('/viscosity/cross/infiniteShearViscosity', viscosity.infiniteShearViscosity))
                                properties.append(('/viscosity/cross/naturalTime', viscosity.naturalTime))
                                properties.append(('/viscosity/cross/powerLawIndex', viscosity.powerLawIndex))
                            elif viscositySpecification == ViscositySpecification.HERSCHEL_BULKLEY:
                                properties.append(
                                    ('/viscosity/herschelBulkley/zeroShearViscosity', viscosity.zeroShearViscosity))
                                properties.append(
                                    ('/viscosity/herschelBulkley/yieldStressThreshold', viscosity.yieldStressThreshold))
                                properties.append(
                                    ('/viscosity/herschelBulkley/consistencyIndex', viscosity.consistencyIndex))
                                properties.append(('/viscosity/herschelBulkley/powerLawIndex', viscosity.powerLawIndex))
                            elif viscositySpecification == ViscositySpecification.BIRD_CARREAU:
                                properties.append(
                                    ('/viscosity/carreau/zeroShearViscosity', viscosity.zeroShearViscosity))
                                properties.append(
                                    ('/viscosity/carreau/infiniteShearViscosity', viscosity.infiniteShearViscosity))
                                properties.append(('/viscosity/carreau/relaxationTime', viscosity.relaxationTime))
                                properties.append(('/viscosity/carreau/powerLawIndex', viscosity.powerLawIndex))
                                properties.append(('/viscosity/carreau/linearityDeviation',
                                                   viscosity.linearityDeviation))
                            elif viscositySpecification == ViscositySpecification.POWER_LAW:
                                properties.append(
                                    ('/viscosity/nonNewtonianPowerLaw/maximumViscosity', viscosity.maximumViscosity))
                                properties.append(
                                    ('/viscosity/nonNewtonianPowerLaw/minimumViscosity', viscosity.minimumViscosity))
                                properties.append(
                                    ('/viscosity/nonNewtonianPowerLaw/consistencyIndex', viscosity.consistencyIndex))
                                properties.append(
                                    ('/viscosity/nonNewtonianPowerLaw/powerLawIndex', viscosity.powerLawIndex))

                            if self._type == MaterialType.SPECIE:
                                mixture = MaterialDB.getMixture(self._mid)
                                xpath = MaterialDB.getXPath(mixture)
                                for subXPath, value in properties:
                                    db.setValue(xpath + subXPath, value)

                                for mid in MaterialDB.getSpecies(mixture):
                                    xpath = MaterialDB.getXPath(mid)
                                    for subXPath, value in properties:
                                        db.setValue(xpath + subXPath, value)
                            else:
                                for subXPath, value in properties:
                                    db.setValue(self._xpath + subXPath, value)

                if ModelsDB.isEnergyModelOn():
                    specification = self._ui.specificHeatType.currentData()
                    db.setValue(self._xpath + '/specificHeat/specification', specification.value, None)
                    if specification == Specification.CONSTANT:
                        db.setValue(self._xpath + '/specificHeat/constant',
                                      self._ui.constantSpecificHeat.text(), self.tr('Specific Heat Value'))
                    elif specification == Specification.POLYNOMIAL:
                        if self._polynomialSpecificHeat:
                            db.setValue(self._xpath + '/specificHeat/polynomial',
                                          self._polynomialSpecificHeat, self.tr('Specific Heat Polynomial'))
                        elif db.getValue(self._xpath + '/specificHeat/polynomial') == '':
                            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                                self.tr('Edit Specific Heat Polynomial.'))
                            return

                    if viscositySpecification != ViscositySpecification.SUTHERLAND:
                        specification = self._ui.thermalConductivityType.currentData()
                        db.setValue(self._xpath + '/thermalConductivity/specification', specification.value, None)
                        if specification == Specification.CONSTANT:
                            db.setValue(
                                self._xpath + '/thermalConductivity/constant',
                                self._ui.constantThermalConductivity.text(), self.tr('Thermal Conductivity Value'))
                        elif specification == Specification.POLYNOMIAL:
                            if self._polynomialThermalConductivity:
                                db.setValue(self._xpath + '/thermalConductivity/polynomial',
                                            self._polynomialThermalConductivity,
                                            self.tr('Thermal Conductivity Polynomial'))
                            elif db.getValue(self._xpath + '/thermalConductivity/polynomial') == '':
                                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                                    self.tr('Edit Thermal Conductivity Polynomial.'))
                                return

                    if self._phase == Phase.SOLID:
                        db.setValue(self._xpath + '/emissivity', self._ui.emissivity.text(), self.tr('Emissivity'))
                    else:
                        db.setValue(self._xpath + '/molecularWeight',
                                      self._ui.molecularWeight.text(), self.tr('Molecular Weight'))
                        if self._phase == Phase.GAS:
                            db.setValue(self._xpath + '/absorptionCoefficient',
                                          self._ui.absorptionCoefficient.text(), self.tr('Absorption Coefficient'))
                        elif self._phase == Phase.LIQUID:
                            db.setValue(self._xpath + '/saturationPressure',
                                          self._ui.saturationPressure.text(), self.tr('Saturation Pressure'))

            self.accept()
        except ConfigurationException as ex:
            await AsyncMessageBox().information(self, self.tr('Model Change Failed'), str(ex))

    def _setupDensitySpecification(self, spec):
        if self._type == MaterialType.SPECIE:
            self._setupSpecificationCombo(self._ui.densityType, [spec])
            self._ui.densityType.setEnabled(False)
        else:
            if self._phase == Phase.GAS:
                self._setupSpecificationCombo(
                    self._ui.densityType, [
                        DensitySpecification.CONSTANT,
                        DensitySpecification.PERFECT_GAS,
                        DensitySpecification.POLYNOMIAL,
                        DensitySpecification.INCOMPRESSIBLE_PERFECT_GAS,
                    ]
                )
            else:
                self._setupSpecificationCombo(
                    self._ui.densityType, [
                        DensitySpecification.CONSTANT,
                    ]
                )

        self._ui.densityType.setCurrentData(spec)

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

        self._ui.specificHeatType.setCurrentData(spec)

    def _setupViscositySpecification(self, spec):
        if self._type == MaterialType.SPECIE:
            self._setupSpecificationCombo(self._ui.viscosityType, [spec])
            self._ui.viscosityType.setEnabled(False)
        else:
            if self._phase == Phase.LIQUID and TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR:
                self._setupSpecificationCombo(
                    self._ui.viscosityType, [
                        ViscositySpecification.CONSTANT,
                        ViscositySpecification.POLYNOMIAL,
                        ViscositySpecification.CROSS_POWER_LAW,
                        ViscositySpecification.HERSCHEL_BULKLEY,
                        ViscositySpecification.BIRD_CARREAU,
                        ViscositySpecification.POWER_LAW
                    ]
                )
            else:   # gas or liquid
                self._setupSpecificationCombo(
                    self._ui.viscosityType, [
                        ViscositySpecification.CONSTANT,
                        ViscositySpecification.SUTHERLAND,
                        ViscositySpecification.POLYNOMIAL,
                    ]
                )

        self._ui.viscosityType.setCurrentData(spec)

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

        self._ui.thermalConductivityType.setCurrentData(spec)

    def _setupSpecificationCombo(self, combo, types):
        for t in types:
            combo.addEnumItem(t, MaterialDB.specificationToText(t))

    def _connectSignalsSlots(self):
        self._ui.densityType.currentDataChanged.connect(self._densityTypeChanged)
        self._ui.specificHeatType.currentDataChanged.connect(self._specificHeatTypeChanged)
        self._ui.viscosityType.currentDataChanged.connect(self._viscosityTypeChanged)
        self._ui.thermalConductivityType.currentDataChanged.connect(self._thermalConductivityTypeChanged)
        self._ui.densityEdit.clicked.connect(self._editDensity)
        self._ui.specificHeatEdit.clicked.connect(self._editSpecificHeat)
        self._ui.viscosityEdit.clicked.connect(self._editViscosity)
        self._ui.thermalConductivityEdit.clicked.connect(self._editThermalConductivity)
        self._ui.ok.clicked.connect(self._accept)

    def _densityTypeChanged(self, specification):
        self._ui.densityEdit.setEnabled(specification == DensitySpecification.POLYNOMIAL)
        self._ui.constantDensity.setEnabled(specification == DensitySpecification.CONSTANT)
        self._ui.pengRobinsonParameters.setVisible(specification == DensitySpecification.REAL_GAS_PENG_ROBINSON)

    def _specificHeatTypeChanged(self, specification):
        self._ui.specificHeatEdit.setEnabled(specification == Specification.POLYNOMIAL)
        self._ui.constantSpecificHeat.setEnabled(specification == Specification.CONSTANT)

    @qasync.asyncSlot()
    async def _viscosityTypeChanged(self, specification):
        self._ui.viscosityEdit.setEnabled(specification == ViscositySpecification.POLYNOMIAL
                                          or MaterialDB.isNonNewtonianSpecification(specification))
        self._ui.constantViscosity.setEnabled(specification == ViscositySpecification.CONSTANT)

        if self._phase == Phase.GAS:
            if specification == ViscositySpecification.SUTHERLAND:
                self._ui.sutherlandCoefficient.setEnabled(True)
                self._ui.sutherlandTemperature.setEnabled(True)
                self._ui.thermalConductivity.setEnabled(False)
            else:
                self._ui.sutherlandCoefficient.setEnabled(False)
                self._ui.sutherlandTemperature.setEnabled(False)
                self._ui.thermalConductivity.setEnabled(True)
                self._ui.thermalConductivityType.setCurrentText(self._ui.viscosityType.currentText())
        elif self._phase == Phase.LIQUID:
            if MaterialDB.isNonNewtonianSpecification(specification):
                if ModelsDB.isEnergyModelOn():
                    self._ui.thermalConductivityType.setEnabled(False)
                    self._ui.thermalConductivityType.setCurrentData(Specification.CONSTANT)
            else:
                self._ui.thermalConductivityType.setEnabled(self._type != MaterialType.SPECIE)
                self._ui.thermalConductivityType.setCurrentText(self._ui.viscosityType.currentText())

    def _thermalConductivityTypeChanged(self, specification):
        self._ui.thermalConductivityEdit.setEnabled(specification == Specification.POLYNOMIAL)
        self._ui.constantThermalConductivity.setEnabled(specification == Specification.CONSTANT)
        if not MaterialDB.isNonNewtonianSpecification(self._ui.viscosityType.currentData()):
            self._ui.viscosityType.setCurrentText(self._ui.thermalConductivityType.currentText())

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
        specification = self._ui.viscosityType.currentData()
        if specification == ViscositySpecification.POLYNOMIAL:
            if self._viscosities[specification] is None:
                self._viscosities[specification] = db.getValue(self._xpath + '/viscosity/polynomial')

            self._dialog = PolynomialDialog(self, self.tr('Polynomial Viscosity'), self._viscosities[specification])
        elif specification == ViscositySpecification.CROSS_POWER_LAW:
            self._dialog = ViscosityCrossDialog(self, self._xpath, self._viscosities[specification])
        elif specification == ViscositySpecification.HERSCHEL_BULKLEY:
            self._dialog = ViscosityHerschelBulkleyDialog(self, self._xpath, self._viscosities[specification])
        elif specification == ViscositySpecification.BIRD_CARREAU:
            self._dialog = ViscosityCarreauDialog(self, self._xpath, self._viscosities[specification])
        elif specification == ViscositySpecification.POWER_LAW:
            self._dialog = ViscosityNonNewtonianPowerLawDialog(self, self._xpath, self._viscosities[specification])

        self._dialog.accepted.connect(lambda: self._viscosityEditAccepted(specification))
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

    def _viscosityEditAccepted(self, specification):
        self._viscosities[specification] = self._dialog.getValues()

    def _polynomialThermalConductivityAccepted(self):
        self._polynomialThermalConductivity = self._dialog.getValues()
