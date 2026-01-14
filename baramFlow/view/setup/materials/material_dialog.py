#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from typing import cast
from PySide6.QtWidgets import QFormLayout
import qasync

from baramFlow.base.base import Function1Scalar
from baramFlow.base.constants import Function1Type
from baramFlow.base.material.database import materialsBase
from baramFlow.base.material.material import Phase, MaterialType, SpecificHeatSpecification, DensitySpecification, TransportSpecification
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.view.setup.materials.thermos_dialog import ThermosDialog
from baramFlow.view.widgets.number_input_dialog import PolynomialDialog
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from libbaram.qt_utils import allDirectChildrenAreHidden
from widgets.async_message_box import AsyncMessageBox


from .material_dialog_ui import Ui_MaterialDialog
from .janaf_dialog import JanafDialog
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
        self._specificHeats = {
            SpecificHeatSpecification.POLYNOMIAL: None,
            SpecificHeatSpecification.JANAF: None
        }
        self._polynomialThermalConductivity = None
        self._polynomialDialog = None
        self._viscosities = {
            TransportSpecification.POLYNOMIAL: None,
            TransportSpecification.CROSS_POWER_LAW: None,
            TransportSpecification.HERSCHEL_BULKLEY: None,
            TransportSpecification.BIRD_CARREAU: None,
            TransportSpecification.POWER_LAW: None
        }

        energyOn = ModelsDB.isEnergyModelOn()

        layout = cast(QFormLayout, self._ui.otherProperties.layout())

        layout.setRowVisible(self._ui.criticalTemperature, self._phase != Phase.SOLID)
        layout.setRowVisible(self._ui.criticalPressure, self._phase    != Phase.SOLID)
        layout.setRowVisible(self._ui.criticalSpecificVolume, self._phase != Phase.SOLID)
        layout.setRowVisible(self._ui.acentricFactor, self._phase      != Phase.SOLID)
        layout.setRowVisible(self._ui.tripleTemperature, self._phase   != Phase.SOLID)
        layout.setRowVisible(self._ui.triplePressure, self._phase      != Phase.SOLID)

        layout.setRowVisible(self._ui.standardStateEnthalpy, self._phase != Phase.SOLID and energyOn)
        layout.setRowVisible(self._ui.referenceTemperature, self._phase  != Phase.SOLID and energyOn)

        layout.setRowVisible(self._ui.saturationPressure, self._phase  == Phase.LIQUID and energyOn)
        layout.setRowVisible(self._ui.enthalpyOfVaporization, self._phase == Phase.LIQUID and energyOn)
        layout.setRowVisible(self._ui.boilingTemperature, self._phase  == Phase.LIQUID and energyOn)
        layout.setRowVisible(self._ui.dropletSurfaceTension, self._phase  == Phase.LIQUID)

        layout.setRowVisible(self._ui.absorptionCoefficient, False)  # hide until Radiation is implemented
        layout.setRowVisible(self._ui.emissivity, False)  # hide until Radiation is implemented

        self._ui.specificHeatGroup.setVisible(energyOn)

        self._ui.viscositySutherlandGroup.setVisible(self._phase == Phase.GAS)

        self._ui.viscosityGroup.setVisible(self._phase != Phase.SOLID)
        self._ui.thermalConductivityGroup.setVisible(energyOn)

        if TurbulenceModelsDB.getModel() == TurbulenceModel.INVISCID \
            or (self._ui.viscosityGroup.isHidden() and self._ui.thermalConductivityGroup.isHidden()):
            self._ui.transportGroup.hide()

        if allDirectChildrenAreHidden(self._ui.otherProperties):
            self._ui.otherPropertiesContainer.hide()

        if self._phase == Phase.LIQUID:
            if energyOn:
                types = [Function1Type.CONSTANT, Function1Type.TABLE]
            else:
                types = [Function1Type.CONSTANT]

            self._ui.saturationPressure.setup(types)
            self._ui.enthalpyOfVaporization.setup(types)
            self._ui.dropletSurfaceTension.setup(types)

        self._connectSignalsSlots()

        if CaseManager().isActive():
            self._ui.dialogContents.setEnabled(False)
            self._ui.ok.setEnabled(False)

        self._load()

    def _load(self):
        self._name = MaterialDB.getName(self._mid)
        self._ui.name.setText(self._name)

        db = coredb.CoreDB()

        # Density

        if ModelsDB.isEnergyModelOn():
            densitySpec = DensitySpecification(db.getValue(self._xpath + '/density/specification'))
        else:
            densitySpec = DensitySpecification.CONSTANT

        self._setupDensitySpec(densitySpec)

        self._ui.constantDensity.setText(db.getValue(self._xpath + '/density/constant'))

        if self._phase == Phase.GAS:
            self._ui.boussinesqRho0.setText(db.getValue(self._xpath + '/density/boussinesq/rho0'))
            self._ui.boussinesqT0.setText(db.getValue(self._xpath + '/density/boussinesq/T0'))
            self._ui.boussinesqBeta.setText(db.getValue(self._xpath + '/density/boussinesq/beta'))
        elif self._phase == Phase.LIQUID:
            self._ui.perfectFluidRho0.setText(db.getValue(self._xpath + '/density/perfectFluid/rho0'))
            self._ui.perfectFluidT.setText(db.getValue(self._xpath + '/density/perfectFluid/T'))
            self._ui.perfectFluidBeta.setText(db.getValue(self._xpath + '/density/perfectFluid/beta'))

        # Specific Heat

        if ModelsDB.isEnergyModelOn():
            specificHeatSpec = SpecificHeatSpecification(db.getValue(self._xpath + '/specificHeat/specification'))
        else:
            specificHeatSpec = SpecificHeatSpecification.CONSTANT

        self._setupSpecificHeatSpec(specificHeatSpec)

        self._ui.constantSpecificHeat.setText(db.getValue(self._xpath + '/specificHeat/constant'))

        # Transport

        if ModelsDB.isEnergyModelOn() or (TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR and self._phase != Phase.SOLID):
            transportSpecification = TransportSpecification(db.getValue(self._xpath + '/transport/specification'))
        else:
            transportSpecification = TransportSpecification.CONSTANT

        self._setupTransportSpecification(transportSpecification)

        if self._phase != Phase.SOLID:
            self._ui.viscosityConstant.setText(db.getValue(self._xpath + '/transport/viscosity'))

        self._ui.thermalConductivityConstant.setText(db.getValue(self._xpath + '/transport/thermalConductivity'))

        if self._phase == Phase.GAS:
            self._ui.sutherlandCoefficient.setText(db.getValue(self._xpath + '/transport/sutherland/coefficient'))
            self._ui.sutherlandTemperature.setText(db.getValue(self._xpath + '/transport/sutherland/temperature'))

        self._ui.molecularWeight.setText(db.getValue(self._xpath + '/molecularWeight'))

        if self._phase == Phase.SOLID:
            self._ui.emissivity.setText(db.getValue(self._xpath + '/emissivity'))

        else:
            self._ui.criticalTemperature.setText(   db.getValue(self._xpath + '/criticalTemperature'))
            self._ui.criticalPressure.setText(      db.getValue(self._xpath + '/criticalPressure'))
            self._ui.criticalSpecificVolume.setText(db.getValue(self._xpath + '/criticalSpecificVolume'))

            self._ui.tripleTemperature.setText(     db.getValue(self._xpath + '/tripleTemperature'))
            self._ui.triplePressure.setText(        db.getValue(self._xpath + '/triplePressure'))

            self._ui.standardStateEnthalpy.setText( db.getValue(self._xpath + '/standardStateEnthalpy'))
            self._ui.referenceTemperature.setText(  db.getValue(self._xpath + '/referenceTemperature'))

            self._ui.acentricFactor.setText(db.getValue(self._xpath + '/acentricFactor'))

            if self._phase == Phase.LIQUID:
                self._ui.boilingTemperature.setText(   db.getValue(self._xpath + '/normalBoilingTemperature'))

                # print(etree.tostring(db.getElement(self._xpath), xml_declaration=True, encoding='UTF-8'))
                self._saturationPressure = Function1Scalar.fromElement(db.getElement(self._xpath + '/saturationPressure'))
                self._ui.saturationPressure.setData(self._saturationPressure)

                self._enthalpyOfVaporization = Function1Scalar.fromElement(db.getElement(self._xpath + '/enthalpyOfVaporization'))
                self._ui.enthalpyOfVaporization.setData(self._enthalpyOfVaporization)

                self._dropletSurfaceTension = Function1Scalar.fromElement(db.getElement(self._xpath + '/dropletSurfaceTension'))
                self._ui.dropletSurfaceTension.setData(self._dropletSurfaceTension)

            elif self._phase == Phase.GAS:
                self._ui.absorptionCoefficient.setText(db.getValue(self._xpath + '/absorptionCoefficient'))


    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name != self._name and MaterialDB.isMaterialExists(name):
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr(f'Material name "{name}" is already exists.'))
            return

        densitySpec = self._ui.densitySpec.currentData()

        if ModelsDB.isEnergyModelOn():  # specific heat is hidden if energer is turned off
            specificHeatSpec = self._ui.specificHeatSpec.currentData()
        else:
            specificHeatSpec = SpecificHeatSpecification.CONSTANT

        transportSpec = self._ui.transportSpec.currentData()

        if  self._type != MaterialType.SPECIE and not materialsBase.validateThermos(self._type, self._phase, densitySpec, specificHeatSpec, transportSpec):
            highlights = (densitySpec, specificHeatSpec, transportSpec)
            dialog = ThermosDialog(self._type, self._phase, highlights, self)

            try:
                densitySpec, specificHeatSpec, transportSpec = await dialog.show()
            except asyncio.exceptions.CancelledError:
                return

            self._ui.densitySpec.setCurrentIndex(self._ui.densitySpec.findData(densitySpec))
            self._ui.specificHeatSpec.setCurrentIndex(self._ui.specificHeatSpec.findData(specificHeatSpec))
            self._ui.transportSpec.setCurrentIndex(self._ui.transportSpec.findData(transportSpec))

            return

        try:
            with coredb.CoreDB() as db:
                db.setValue(self._xpath + '/name', name, self.tr('Name'))

                db.setValue(self._xpath + '/density/specification', densitySpec.value, None)

                if densitySpec == DensitySpecification.CONSTANT:
                    db.setValue(self._xpath + '/density/constant', self._ui.constantDensity.text(),
                                self.tr('Density Value'))

                elif densitySpec == DensitySpecification.POLYNOMIAL:
                    if self._polynomialDensity:
                        db.setValue(self._xpath + '/density/polynomial',
                                      self._polynomialDensity, self.tr('Density Polynomial'))
                    elif db.getValue(self._xpath + '/density/polynomial') == '':
                        await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                            self.tr('Edit Density Polynomial.'))
                        return

                elif densitySpec == DensitySpecification.REAL_GAS_PENG_ROBINSON:
                    db.setValue(self._xpath + '/density/constant', self._ui.constantDensity.text(),
                                self.tr('Density Value'))

                elif densitySpec == DensitySpecification.BOUSSINESQ:
                    db.setValue(self._xpath + '/density/boussinesq/rho0', self._ui.boussinesqRho0.text(),
                                self.tr('Reference Density'))
                    db.setValue(self._xpath + '/density/boussinesq/T0', self._ui.boussinesqT0.text(),
                                self.tr('Reference Temperature'))
                    db.setValue(self._xpath + '/density/boussinesq/beta', self._ui.boussinesqBeta.text(),
                                self.tr('Thermal Expansion Coefficient'))

                elif densitySpec == DensitySpecification.PERFECT_FLUID:
                    db.setValue(self._xpath + '/density/perfectFluid/rho0', self._ui.perfectFluidRho0.text(),
                                self.tr('Reference Density'))
                    db.setValue(self._xpath + '/density/perfectFluid/T', self._ui.perfectFluidT.text(),
                                self.tr('Reference Temperature'))
                    db.setValue(self._xpath + '/density/perfectFluid/beta', self._ui.perfectFluidBeta.text(),
                                self.tr('Compressibility'))

                if ModelsDB.isEnergyModelOn():  # specific heat is hidden if energer is turned off
                    db.setValue(self._xpath + '/specificHeat/specification', specificHeatSpec.value, None)

                    if specificHeatSpec == SpecificHeatSpecification.CONSTANT:
                        db.setValue(self._xpath + '/specificHeat/constant',
                                      self._ui.constantSpecificHeat.text(), self.tr('Specific Heat Value'))

                    else:
                        specificHeat = self._specificHeats[specificHeatSpec]
                        if specificHeatSpec == SpecificHeatSpecification.POLYNOMIAL:
                            if specificHeat:
                                db.setValue(self._xpath + '/specificHeat/polynomial', specificHeat,
                                            self.tr('Specific Heat Polynomial'))
                            elif db.getValue(self._xpath + '/specificHeat/polynomial') == '':
                                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                                    self.tr('Edit Specific Heat Polynomial.'))
                                return

                        elif specificHeatSpec == SpecificHeatSpecification.JANAF:
                            if specificHeat:
                                db.setValue(self._xpath + '/specificHeat/janaf/lowTemperature',
                                            specificHeat.lowTemperature)
                                db.setValue(self._xpath + '/specificHeat/janaf/commonTemperature',
                                            specificHeat.commonTemperature)
                                db.setValue(self._xpath + '/specificHeat/janaf/highTemperature',
                                            specificHeat.highTemperature)
                                db.setValue(self._xpath + '/specificHeat/janaf/lowCoefficients',
                                            specificHeat.lowCoefficients)
                                db.setValue(self._xpath + '/specificHeat/janaf/highCoefficients',
                                            specificHeat.highCoefficients)

                else:  # Energy Off
                    specificHeatSpec = SpecificHeatSpecification.CONSTANT

                db.setValue(self._xpath + '/transport/specification', transportSpec.value, None)

                if self._phase != Phase.SOLID:
                    if transportSpec == TransportSpecification.CONSTANT:
                        db.setValue(self._xpath + '/transport/viscosity',
                                      self._ui.viscosityConstant.text(), self.tr('Viscosity Value'))

                    elif transportSpec == TransportSpecification.SUTHERLAND:
                        db.setValue(self._xpath + '/transport/sutherland/coefficient',
                                      self._ui.sutherlandCoefficient.text(), self.tr('Sutherland Coefficient'))
                        db.setValue(self._xpath + '/transport/sutherland/temperature',
                                      self._ui.sutherlandTemperature.text(), self.tr('Sutherland Temperature'))

                    elif transportSpec == TransportSpecification.POLYNOMIAL:
                            viscosity = self._viscosities[transportSpec]
                            if viscosity:
                                db.setValue(self._xpath + '/transport/polynomial/viscosity', viscosity,
                                            self.tr('Viscosity Polynomial'))
                            elif db.getValue(self._xpath + '/transport/polynomial/viscosity') == '':
                                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                                    self.tr('Edit Viscosity Polynomial.'))
                                return

                    elif viscosity := self._viscosities[transportSpec]:  # Non-Newtonian Fluid models
                        properties = []
                        if transportSpec == TransportSpecification.CROSS_POWER_LAW:
                            properties.append(('/transport/cross/zeroShearViscosity', viscosity.zeroShearViscosity))
                            properties.append(
                                ('/transport/cross/infiniteShearViscosity', viscosity.infiniteShearViscosity))
                            properties.append(('/transport/cross/naturalTime', viscosity.naturalTime))
                            properties.append(('/transport/cross/powerLawIndex', viscosity.powerLawIndex))
                        elif transportSpec == TransportSpecification.HERSCHEL_BULKLEY:
                            properties.append(
                                ('/transport/herschelBulkley/zeroShearViscosity', viscosity.zeroShearViscosity))
                            properties.append(
                                ('/transport/herschelBulkley/yieldStressThreshold', viscosity.yieldStressThreshold))
                            properties.append(
                                ('/transport/herschelBulkley/consistencyIndex', viscosity.consistencyIndex))
                            properties.append(('/transport/herschelBulkley/powerLawIndex', viscosity.powerLawIndex))
                        elif transportSpec == TransportSpecification.BIRD_CARREAU:
                            properties.append(
                                ('/transport/carreau/zeroShearViscosity', viscosity.zeroShearViscosity))
                            properties.append(
                                ('/transport/carreau/infiniteShearViscosity', viscosity.infiniteShearViscosity))
                            properties.append(('/transport/carreau/relaxationTime', viscosity.relaxationTime))
                            properties.append(('/transport/carreau/powerLawIndex', viscosity.powerLawIndex))
                            properties.append(('/transport/carreau/linearityDeviation',
                                                viscosity.linearityDeviation))
                        elif transportSpec == TransportSpecification.POWER_LAW:
                            properties.append(
                                ('/transport/nonNewtonianPowerLaw/maximumViscosity', viscosity.maximumViscosity))
                            properties.append(
                                ('/transport/nonNewtonianPowerLaw/minimumViscosity', viscosity.minimumViscosity))
                            properties.append(
                                ('/transport/nonNewtonianPowerLaw/consistencyIndex', viscosity.consistencyIndex))
                            properties.append(
                                ('/transport/nonNewtonianPowerLaw/powerLawIndex', viscosity.powerLawIndex))

                        # All the species in a mixture should have same configuration for Non-Newtonian fluid
                        # because it's configured in "turbulenceProperties" dict file in "OpenFOAM"
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
                    if transportSpec == TransportSpecification.CONSTANT:
                        db.setValue(
                            self._xpath + '/transport/thermalConductivity',
                            self._ui.thermalConductivityConstant.text(), self.tr('Thermal Conductivity Value'))

                    elif transportSpec == TransportSpecification.POLYNOMIAL:
                        if self._polynomialThermalConductivity:
                            db.setValue(self._xpath + '/transport/polynomial/thermalConductivity',
                                        self._polynomialThermalConductivity,
                                        self.tr('Thermal Conductivity Polynomial'))
                        elif db.getValue(self._xpath + '/transport/polynomial/thermalConductivity') == '':
                            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                                self.tr('Edit Thermal Conductivity Polynomial.'))
                            return


                db.setValue(self._xpath + '/molecularWeight',
                                self._ui.molecularWeight.text(), self.tr('Molecular Weight'))

                if self._phase != Phase.SOLID:
                    db.setValue(self._xpath + '/criticalTemperature',
                                  self._ui.criticalTemperature.text(), self.tr('Critical Temperature'))
                    db.setValue(self._xpath + '/criticalPressure',
                                  self._ui.criticalPressure.text(), self.tr('Critical Pressure'))
                    db.setValue(self._xpath + '/criticalSpecificVolume',
                                  self._ui.criticalSpecificVolume.text(), self.tr('Critical Specific Volume'))
                    db.setValue(self._xpath + '/tripleTemperature',
                                  self._ui.tripleTemperature.text(), self.tr('Triple Point Temperature'))
                    db.setValue(self._xpath + '/triplePressure',
                                  self._ui.triplePressure.text(), self.tr('Triple Point Pressure'))
                    db.setValue(self._xpath + '/standardStateEnthalpy',
                                  self._ui.standardStateEnthalpy.text(), self.tr('Standard State Enthalpy'))
                    db.setValue(self._xpath + '/referenceTemperature',
                                  self._ui.referenceTemperature.text(), self.tr('Reference Temperature'))
                    db.setValue(self._xpath + '/acentricFactor',
                                  self._ui.acentricFactor.text(), self.tr('Acentric Factor'))

                    if self._phase == Phase.LIQUID:
                        db.setValue(self._xpath + '/normalBoilingTemperature',
                                    self._ui.boilingTemperature.text(), self.tr('Boiling Temperature'))

                        self._ui.saturationPressure.updateData(self._saturationPressure)
                        db.removeElement(self._xpath + '/saturationPressure')
                        db.addElementFromString(self._xpath,
                                                '<saturationPressure xmlns="http://www.baramcfd.org/baram">'
                                                f'{self._saturationPressure.toXML()}'
                                                '</saturationPressure>')

                        self._ui.enthalpyOfVaporization.updateData(self._enthalpyOfVaporization)
                        db.removeElement(self._xpath + '/enthalpyOfVaporization')
                        db.addElementFromString(self._xpath,
                                                '<enthalpyOfVaporization xmlns="http://www.baramcfd.org/baram">'
                                                f'{self._enthalpyOfVaporization.toXML()}'
                                                '</enthalpyOfVaporization>')

                        self._ui.dropletSurfaceTension.updateData(self._dropletSurfaceTension)
                        db.removeElement(self._xpath + '/dropletSurfaceTension')
                        db.addElementFromString(self._xpath,
                                                '<dropletSurfaceTension xmlns="http://www.baramcfd.org/baram">'
                                                f'{self._dropletSurfaceTension.toXML()}'
                                                '</dropletSurfaceTension>')

                if ModelsDB.isEnergyModelOn():
                    if self._phase == Phase.SOLID:
                        db.setValue(self._xpath + '/emissivity', self._ui.emissivity.text(), self.tr('Emissivity'))
                    else:
                        if self._phase == Phase.GAS:
                            db.setValue(self._xpath + '/absorptionCoefficient',
                                          self._ui.absorptionCoefficient.text(), self.tr('Absorption Coefficient'))

            self.accept()
        except ConfigurationException as ex:
            await AsyncMessageBox().information(self, self.tr('Model Change Failed'), str(ex))

    def _setupDensitySpec(self, spec):
        self._ui.densitySpec.clear()

        if self._type == MaterialType.SPECIE:
            densitySpecs = [spec]
        else:
            densitySpecs = MaterialDB.availableDensitySpec(self._type, self._phase)

        texts = [MaterialDB.densitySpecToText(s) for s in densitySpecs]
        self._ui.densitySpec.setup(texts, densitySpecs, spec)

    def _setupSpecificHeatSpec(self, spec):
        self._ui.specificHeatSpec.clear()

        if self._type == MaterialType.SPECIE:
            specificHeatSpecs = [spec]
        else:
            specificHeatSpecs = MaterialDB.availableSpecificHeatSpecs(self._type, self._phase)

        texts = [MaterialDB.specificHeatSpecToText(s) for s in specificHeatSpecs]
        self._ui.specificHeatSpec.setup(texts, specificHeatSpecs, spec)

    def _setupTransportSpecification(self, spec):
        self._ui.transportSpec.clear()

        if self._type == MaterialType.SPECIE:
            transportSpecs = [spec]
        else:
            transportSpecs = MaterialDB.availableTransportSpecs(self._type, self._phase)

        texts = [MaterialDB.transportSpecToText(s) for s in transportSpecs]
        self._ui.transportSpec.setup(texts, transportSpecs, spec)

    def _connectSignalsSlots(self):
        self._ui.densitySpec.currentIndexChanged.connect(self._densitySpecChanged)
        self._ui.specificHeatSpec.currentIndexChanged.connect(self._specificHeatSpecChanged)
        self._ui.transportSpec.currentIndexChanged.connect(self._transportSpecChanged)
        self._ui.densityEdit.clicked.connect(self._editDensity)
        self._ui.specificHeatEdit.clicked.connect(self._editSpecificHeat)
        self._ui.viscosityEdit.clicked.connect(self._editViscosity)
        self._ui.thermalConductivityEdit.clicked.connect(self._editThermalConductivity)
        self._ui.ok.clicked.connect(self._accept)

    def _densitySpecChanged(self, index):
        specification = self._ui.densitySpec.currentData()

        self._ui.densityEdit.setEnabled(specification == DensitySpecification.POLYNOMIAL)
        self._ui.constantDensity.setEnabled(specification == DensitySpecification.CONSTANT)
        self._ui.boussinesq.setVisible(specification == DensitySpecification.BOUSSINESQ)
        self._ui.perfectFluid.setVisible(specification == DensitySpecification.PERFECT_FLUID)

    def _specificHeatSpecChanged(self, index):
        specification = self._ui.specificHeatSpec.currentData()

        self._ui.specificHeatEdit.setEnabled(specification != SpecificHeatSpecification.CONSTANT)
        self._ui.constantSpecificHeat.setEnabled(specification == SpecificHeatSpecification.CONSTANT)

    @qasync.asyncSlot()
    async def _transportSpecChanged(self, index):
        specification = self._ui.transportSpec.currentData()

        self._ui.viscosityConstantGroup.setVisible(specification == TransportSpecification.CONSTANT)
        self._ui.viscositySutherlandGroup.setVisible(specification == TransportSpecification.SUTHERLAND)
        self._ui.viscosityEditGroup.setVisible(specification == TransportSpecification.POLYNOMIAL or MaterialDB.isNonNewtonianSpecification(specification))

        if specification == TransportSpecification.SUTHERLAND:
            self._ui.thermalConductivityConstantGroup.hide()
            self._ui.thermalConductivityEditGroup.hide()
        elif specification == TransportSpecification.POLYNOMIAL:
            self._ui.thermalConductivityConstantGroup.hide()
            self._ui.thermalConductivityEditGroup.show()
        else:
            self._ui.thermalConductivityConstantGroup.show()
            self._ui.thermalConductivityEditGroup.hide()

    def _editDensity(self):
        db = coredb.CoreDB()
        if self._polynomialDensity is None:
            self._polynomialDensity = db.getValue(self._xpath + '/density/polynomial')

        self._dialog = PolynomialDialog(self, self.tr('Polynomial Density'), self._polynomialDensity)
        self._dialog.accepted.connect(self._polynomialDensityAccepted)
        self._dialog.open()

    def _editSpecificHeat(self):
        db = coredb.CoreDB()
        specification = self._ui.specificHeatSpec.currentData()
        if specification == SpecificHeatSpecification.POLYNOMIAL:
            if self._specificHeats[specification] is None:
                self._specificHeats[specification] = db.getValue(self._xpath + '/specificHeat/polynomial')

            self._dialog = PolynomialDialog(self, self.tr('Polynomial Specific Heat'),
                                            self._specificHeats[specification])
        elif specification == SpecificHeatSpecification.JANAF:
            self._dialog = JanafDialog(self, self.tr('JANAF Specific Heat'),
                                                     self._xpath, self._specificHeats[specification])
        self._dialog.accepted.connect(lambda: self._speicificHeatEditAccepted(specification))
        self._dialog.open()

    @qasync.asyncSlot()
    async def _editViscosity(self):
        db = coredb.CoreDB()
        specification = self._ui.transportSpec.currentData()
        if specification == TransportSpecification.POLYNOMIAL:
            if self._viscosities[specification] is None:
                self._viscosities[specification] = db.getValue(self._xpath + '/transport/polynomial/viscosity')

            self._dialog = PolynomialDialog(self, self.tr('Polynomial Viscosity'), self._viscosities[specification])
        elif specification == TransportSpecification.CROSS_POWER_LAW:
            self._dialog = ViscosityCrossDialog(self, self._xpath, self._viscosities[specification])
        elif specification == TransportSpecification.HERSCHEL_BULKLEY:
            self._dialog = ViscosityHerschelBulkleyDialog(self, self._xpath, self._viscosities[specification])
        elif specification == TransportSpecification.BIRD_CARREAU:
            self._dialog = ViscosityCarreauDialog(self, self._xpath, self._viscosities[specification])
        elif specification == TransportSpecification.POWER_LAW:
            self._dialog = ViscosityNonNewtonianPowerLawDialog(self, self._xpath, self._viscosities[specification])

        self._dialog.accepted.connect(lambda: self._viscosityEditAccepted(specification))
        self._dialog.open()

    def _editThermalConductivity(self):
        db = coredb.CoreDB()
        if self._polynomialThermalConductivity is None:
            self._polynomialThermalConductivity = db.getValue(self._xpath + '/transport/polynomial/thermalConductivity')

        self._dialog = PolynomialDialog(self, self.tr('Polynomial Thermal Conductivity'),
                                        self._polynomialThermalConductivity)
        self._dialog.accepted.connect(self._polynomialThermalConductivityAccepted)
        self._dialog.open()

    def _polynomialDensityAccepted(self):
        self._polynomialDensity = self._dialog.getValues()

    def _speicificHeatEditAccepted(self, specification):
        self._specificHeats[specification] = self._dialog.getValues()

    def _viscosityEditAccepted(self, specification):
        self._viscosities[specification] = self._dialog.getValues()

    def _polynomialThermalConductivityAccepted(self):
        self._polynomialThermalConductivity = self._dialog.getValues()
