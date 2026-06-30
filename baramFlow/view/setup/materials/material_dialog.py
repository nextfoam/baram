#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from copy import deepcopy
from typing import cast
from PySide6.QtWidgets import QFormLayout, QWidget, QDialog
import qasync

from baramFlow.base.base import NumberList
from baramFlow.base.constants import Function1Type
from baramFlow.base.material.database import materialsBase
from baramFlow.base.material.constants import Phase, MaterialType, NON_NEWTONIAN_VISCOSITY_SPECIFICATIONS
from baramFlow.base.material.constants import SpecificHeatSpecification, DensitySpecification, TransportSpecification
from baramFlow.base.material.material import Material
from baramFlow.base.material.transport import Transport
from baramFlow.base.material.specific_heat import JanafSpecificHeat, SpecificHeat
from baramFlow.base.material.transport import CrossViscosity, HerschelBulkleyViscosity, CarreauViscosity
from baramFlow.base.material.transport import NonNewtonianPowerLawViscosity
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.services.material.material_service import MaterialService
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
    def __init__(self, parent: QWidget, mid: str):
        super().__init__(parent)
        self._ui = Ui_MaterialDialog()
        self._ui.setupUi(self)

        self._data: Material = MaterialService.getMaterial(mid)
        self._mid: str = mid
        self._xpath = MaterialDB.getXPath(mid)
        self._type = MaterialDB.getType(self._mid)

        self._polynomialDensity: NumberList = self._data.density.polynomial
        self._specificHeat: SpecificHeat = deepcopy(self._data.specificHeat)
        self._transport: Transport = deepcopy(self._data.transport)

        self._dialog: QDialog

        energyOn = ModelsDB.isEnergyModelOn()

        layout = cast(QFormLayout, self._ui.otherProperties.layout())

        layout.setRowVisible(self._ui.criticalTemperature,      self._data.phase != Phase.SOLID)
        layout.setRowVisible(self._ui.criticalPressure,         self._data.phase != Phase.SOLID)
        layout.setRowVisible(self._ui.criticalSpecificVolume,   self._data.phase != Phase.SOLID)
        layout.setRowVisible(self._ui.acentricFactor,           self._data.phase != Phase.SOLID)
        layout.setRowVisible(self._ui.tripleTemperature,        self._data.phase != Phase.SOLID)
        layout.setRowVisible(self._ui.triplePressure,           self._data.phase != Phase.SOLID)

        layout.setRowVisible(self._ui.standardStateEnthalpy,    self._data.phase != Phase.SOLID and energyOn)
        layout.setRowVisible(self._ui.referenceTemperature,     self._data.phase != Phase.SOLID and energyOn)

        layout.setRowVisible(self._ui.saturationPressure,       self._data.phase == Phase.LIQUID and energyOn)
        layout.setRowVisible(self._ui.enthalpyOfVaporization,   self._data.phase == Phase.LIQUID and energyOn)
        layout.setRowVisible(self._ui.boilingTemperature,       self._data.phase == Phase.LIQUID and energyOn)
        layout.setRowVisible(self._ui.dropletSurfaceTension,    self._data.phase == Phase.LIQUID)

        layout.setRowVisible(self._ui.absorptionCoefficient, False)  # hide until Radiation is implemented
        layout.setRowVisible(self._ui.emissivity, False)  # hide until Radiation is implemented

        layout.setRowVisible(self._ui.virialCoeff, False)

        self._ui.specificHeatGroup.setVisible(energyOn)

        self._ui.viscositySutherlandGroup.setVisible(self._data.phase == Phase.GAS)

        self._ui.viscosityGroup.setVisible(self._data.phase != Phase.SOLID)
        self._ui.thermalConductivityGroup.setVisible(energyOn)

        if TurbulenceModelsDB.getModel() == TurbulenceModel.INVISCID \
            or (self._ui.viscosityGroup.isHidden() and self._ui.thermalConductivityGroup.isHidden()):
            self._ui.transportGroup.hide()

        if allDirectChildrenAreHidden(self._ui.otherProperties):
            self._ui.otherPropertiesContainer.hide()

        if self._data.phase == Phase.LIQUID:
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
        self._ui.name.setText(self._data.name)

        db = coredb.CoreDB()

        # Density

        if ModelsDB.isEnergyModelOn():
            densitySpec = self._data.density.specification
        else:
            densitySpec = DensitySpecification.CONSTANT

        self._setupDensitySpec(densitySpec)

        self._ui.constantDensity.setPFloat(self._data.density.constant)

        if self._data.phase == Phase.GAS:
            self._ui.boussinesqRho0.setPFloat(self._data.density.boussinesq.rho0)
            self._ui.boussinesqT0.setPFloat(self._data.density.boussinesq.t0)
            self._ui.boussinesqBeta.setPFloat(self._data.density.boussinesq.beta)
        elif self._data.phase == Phase.LIQUID:
            self._ui.perfectFluidRho0.setPFloat(self._data.density.perfectFluid.rho0)
            self._ui.perfectFluidT.setPFloat(self._data.density.perfectFluid.t)
            self._ui.perfectFluidBeta.setPFloat(self._data.density.perfectFluid.beta)

        # Specific Heat

        if ModelsDB.isEnergyModelOn():
            specificHeatSpec = self._data.specificHeat.specification
        else:
            specificHeatSpec = SpecificHeatSpecification.CONSTANT

        self._setupSpecificHeatSpec(specificHeatSpec)

        self._ui.constantSpecificHeat.setPFloat(self._data.specificHeat.constant)

        # Transport

        if ModelsDB.isEnergyModelOn() or (TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR and self._data.phase != Phase.SOLID):
            transportSpecification = self._data.transport.specification
        else:
            transportSpecification = TransportSpecification.CONSTANT

        self._setupTransportSpecification(transportSpecification)

        if self._data.phase != Phase.SOLID:
            self._ui.viscosityConstant.setPFloat(self._data.transport.viscosity)

        self._ui.thermalConductivityConstant.setPFloat(self._data.transport.thermalConductivity)

        if self._data.phase == Phase.GAS:
            self._ui.sutherlandCoefficient.setPFloat(self._data.transport.sutherland.coefficient)
            self._ui.sutherlandTemperature.setPFloat(self._data.transport.sutherland.temperature)

        self._ui.molecularWeight.setPFloat(self._data.molecularWeight)

        if self._data.phase == Phase.SOLID:
            self._ui.emissivity.setPFloat(self._data.emissivity)

        else:
            self._ui.criticalTemperature.setPFloat(self._data.criticalTemperature)
            self._ui.criticalPressure.setPFloat(self._data.criticalPressure)
            self._ui.criticalSpecificVolume.setPFloat(self._data.criticalSpecificVolume)

            self._ui.tripleTemperature.setPFloat(self._data.tripleTemperature)
            self._ui.triplePressure.setPFloat(self._data.triplePressure)

            self._ui.standardStateEnthalpy.setPFloat(self._data.standardStateEnthalpy)
            self._ui.referenceTemperature.setPFloat(self._data.referenceTemperature)

            self._ui.acentricFactor.setPFloat(self._data.acentricFactor)

            if self._data.phase == Phase.LIQUID:
                self._ui.boilingTemperature.setPFloat(self._data.normalBoilingTemperature)

                # print(etree.tostring(db.getElement(self._xpath), xml_declaration=True, encoding='UTF-8'))
                self._ui.saturationPressure.setData(self._data.saturationPressure)
                self._ui.enthalpyOfVaporization.setData(self._data.enthalpyOfVaporization)
                self._ui.dropletSurfaceTension.setData(self._data.dropletSurfaceTension)

            elif self._data.phase == Phase.GAS:
                self._ui.absorptionCoefficient.setPFloat(self._data.absorptionCoefficient)

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name != self._data.name and MaterialDB.isMaterialExists(name):
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr(f'Material name "{name}" is already exists.'))
            return

        densitySpec = self._ui.densitySpec.currentData()

        if ModelsDB.isEnergyModelOn():  # specific heat is hidden if energer is turned off
            specificHeatSpec = self._ui.specificHeatSpec.currentData()
        else:
            specificHeatSpec = SpecificHeatSpecification.CONSTANT

        transportSpec = self._ui.transportSpec.currentData()

        if (self._data.type != MaterialType.SPECIE
                and not materialsBase.validateThermos(
                    self._type, self._data.phase, densitySpec, specificHeatSpec, transportSpec)):
            highlights = (densitySpec, specificHeatSpec, transportSpec)
            dialog = ThermosDialog(self._type, self._data.phase, highlights, self)

            try:
                densitySpec, specificHeatSpec, transportSpec = await dialog.show()
            except asyncio.exceptions.CancelledError:
                return

            self._ui.densitySpec.setCurrentIndex(self._ui.densitySpec.findData(densitySpec))
            self._ui.specificHeatSpec.setCurrentIndex(self._ui.specificHeatSpec.findData(specificHeatSpec))
            self._ui.transportSpec.setCurrentIndex(self._ui.transportSpec.findData(transportSpec))

            return

        data = deepcopy(self._data)
        data.name = name

        try:
            data.density.specification = densitySpec

            if densitySpec == DensitySpecification.CONSTANT:
                data.density.constant = self._ui.constantDensity.pFloat(self.tr('Density Value'))
            elif densitySpec == DensitySpecification.POLYNOMIAL:
                if self._polynomialDensity.isEmpty():
                    await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                        self.tr('Edit Density Polynomial.'))
                    return

                data.density.polynomial = self._polynomialDensity
            elif densitySpec == DensitySpecification.REAL_GAS_PENG_ROBINSON:
                data.density.constant = self._ui.constantDensity.pFloat(self.tr('Density Value'))
            elif densitySpec == DensitySpecification.BOUSSINESQ:
                data.density.boussinesq.rho0 = self._ui.boussinesqRho0.pFloat(self.tr('Reference Density'))
                data.density.boussinesq.t0 = self._ui.boussinesqT0.pFloat(self.tr('Reference Temperature'))
                data.density.boussinesq.beta = self._ui.boussinesqBeta.pFloat(self.tr('Thermal Expansion Coefficient'))
            elif densitySpec == DensitySpecification.PERFECT_FLUID:
                data.density.perfectFluid.rho0 = self._ui.perfectFluidRho0.pFloat(self.tr('Reference Density'))
                data.density.perfectFluid.t = self._ui.perfectFluidT.pFloat(self.tr('Reference Temperature'))
                data.density.perfectFluid.beta = self._ui.perfectFluidBeta.pFloat(self.tr('Compressibility'))

            if ModelsDB.isEnergyModelOn():  # specific heat is hidden if energer is turned off
                data.specificHeat.specification = specificHeatSpec

                if specificHeatSpec == SpecificHeatSpecification.CONSTANT:
                    data.specificHeat.constant = self._ui.constantSpecificHeat.pFloat(self.tr('Specific Heat Value'))
                elif specificHeatSpec == SpecificHeatSpecification.POLYNOMIAL:
                    if self._specificHeat.polynomial.isEmpty():
                        await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                            self.tr('Edit Specific Heat Polynomial.'))
                        return

                    data.specificHeat.polynomial = self._specificHeat.polynomial
                elif specificHeatSpec == SpecificHeatSpecification.JANAF:
                    data.specificHeat.janaf = self._specificHeat.janaf

            data.transport.specification = transportSpec

            if self._data.phase != Phase.SOLID:
                if transportSpec == TransportSpecification.CONSTANT:
                    data.transport.viscosity = self._ui.viscosityConstant.pFloat(self.tr('Viscosity Value'))
                elif transportSpec == TransportSpecification.SUTHERLAND:
                    data.transport.sutherland.coefficient = self._ui.sutherlandCoefficient.pFloat(self.tr('Sutherland Coefficient'))
                    data.transport.sutherland.temperature = self._ui.sutherlandTemperature.pFloat(self.tr('Sutherland Temperature'))
                elif transportSpec == TransportSpecification.POLYNOMIAL:
                    if self._transport.polynomial.viscosity.isEmpty():
                        await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                            self.tr('Edit Viscosity Polynomial.'))
                        return

                    data.transport.polynomial.viscosity = self._transport.polynomial.viscosity
                elif transportSpec == TransportSpecification.CROSS_POWER_LAW:
                    data.transport.crossPowerLaw = self._transport.crossPowerLaw
                elif transportSpec == TransportSpecification.HERSCHEL_BULKLEY:
                    data.transport.herschelBulkley = self._transport.herschelBulkley
                elif transportSpec == TransportSpecification.BIRD_CARREAU:
                    data.transport.birdCarreau = self._transport.birdCarreau
                elif transportSpec == TransportSpecification.POWER_LAW:
                    data.transport.nonNewtonianPowerLaw = self._transport.nonNewtonianPowerLaw

            if ModelsDB.isEnergyModelOn():
                if (transportSpec == TransportSpecification.CONSTANT
                        or transportSpec in NON_NEWTONIAN_VISCOSITY_SPECIFICATIONS):
                    data.transport.thermalConductivity = (
                        self._ui.thermalConductivityConstant.pFloat(self.tr('Thermal Conductivity Value')))
                elif transportSpec == TransportSpecification.POLYNOMIAL:
                    if self._transport.polynomial.thermalConductivity.isEmpty():
                        await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                            self.tr('Edit Thermal Conductivity Polynomial.'))
                        return

                    data.transport.polynomial.thermalConductivity = self._transport.polynomial.thermalConductivity

            data.molecularWeight = self._ui.molecularWeight.pFloat(self.tr('Molecular Weight'))

            if self._data.phase != Phase.SOLID:
                data.criticalTemperature = self._ui.criticalTemperature.pFloat(self.tr('Critical Temperature'))
                data.criticalPressure = self._ui.criticalPressure.pFloat(self.tr('Critical Pressure'))
                data.criticalSpecificVolume = self._ui.criticalSpecificVolume.pFloat(self.tr('Critical Specific Volume'))
                data.tripleTemperature = self._ui.tripleTemperature.pFloat(self.tr('Triple Point Temperature'))
                data.triplePressure = self._ui.triplePressure.pFloat(self.tr('Triple Point Pressure'))
                data.standardStateEnthalpy = self._ui.standardStateEnthalpy.pFloat(self.tr('Standard State Enthalpy'))
                data.referenceTemperature = self._ui.referenceTemperature.pFloat(self.tr('Reference Temperature'))
                data.acentricFactor = self._ui.acentricFactor.pFloat(self.tr('Acentric Factor'))

                if self._data.phase == Phase.LIQUID:
                    data.normalBoilingTemperature = self._ui.boilingTemperature.pFloat(self.tr('Boiling Temperature'))

                    data.saturationPressure = self._ui.saturationPressure.data(self.tr('Saturation Pressure'))
                    data.enthalpyOfVaporization = self._ui.enthalpyOfVaporization.data('Latent Heat')
                    data.dropletSurfaceTension = self._ui.dropletSurfaceTension.data(self.tr('Surface Tension'))

            if ModelsDB.isEnergyModelOn():
                if self._data.phase == Phase.SOLID:
                    data.emissivity = self._ui.emissivity.pFloat(self.tr('Emissivity'))
                elif self._data.phase == Phase.GAS:
                    data.absorptionCoefficient = self._ui.absorptionCoefficient.pFloat(self.tr('Absorption Coefficient'))

            data.specieProperties = self._data.specieProperties

            MaterialService.updateMaterial(data)

            self.accept()
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Model Change Failed'), str(e))

    def _setupDensitySpec(self, spec):
        self._ui.densitySpec.clear()

        if self._type == MaterialType.SPECIE:
            densitySpecs = [spec]
        else:
            densitySpecs = MaterialDB.availableDensitySpec(self._type, self._data.phase)

        texts = [MaterialDB.densitySpecToText(s) for s in densitySpecs]
        self._ui.densitySpec.setup(texts, densitySpecs, spec)

    def _setupSpecificHeatSpec(self, spec):
        self._ui.specificHeatSpec.clear()

        if self._type == MaterialType.SPECIE:
            specificHeatSpecs = [spec]
        else:
            specificHeatSpecs = MaterialDB.availableSpecificHeatSpecs(self._type, self._data.phase)

        texts = [MaterialDB.specificHeatSpecToText(s) for s in specificHeatSpecs]
        self._ui.specificHeatSpec.setup(texts, specificHeatSpecs, spec)

    def _setupTransportSpecification(self, spec):
        self._ui.transportSpec.clear()

        if self._type == MaterialType.SPECIE:
            transportSpecs = [spec]
        else:
            transportSpecs = MaterialDB.availableTransportSpecs(self._type, self._data.phase)

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
        def update(data: list[str]):
            self._polynomialDensity = NumberList(values=data)

        self._dialog = PolynomialDialog(self, self.tr('Polynomial Density'), self._polynomialDensity.values)
        self._dialog.dataAccepted.connect(update)
        self._dialog.open()

    def _editSpecificHeat(self):
        def updatePolynomial(data: list[str]):
            self._specificHeat.polynomial.values = data

        def updateJanaf(data: JanafSpecificHeat):
            self._specificHeat.janaf = data

        specification = self._ui.specificHeatSpec.currentData()
        if specification == SpecificHeatSpecification.POLYNOMIAL:
            self._dialog = PolynomialDialog(
                self, self.tr('Polynomial Specific Heat'), self._specificHeat.polynomial.values)
            self._dialog.dataAccepted.connect(updatePolynomial)
        elif specification == SpecificHeatSpecification.JANAF:
            self._dialog = JanafDialog(self, self.tr('JANAF Specific Heat'), self._xpath, self._specificHeat.janaf)
            self._dialog.dataAccepted.connect(updateJanaf)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _editViscosity(self):
        def updatePolynomial(data: list[str]):
            self._transport.polynomial.viscosity.values = data

        def updateCrossPowerLaw(data: CrossViscosity):
            self._transport.crossPowerLaw = data

        def updateHerschelBulkley(data: HerschelBulkleyViscosity):
            self._transport.herschelBulkley = data

        def updateBirdCarreau(data: CarreauViscosity):
            self._transport.birdCarreau = data

        def updateNonNewtonianPowerLaw(data: NonNewtonianPowerLawViscosity):
            self._transport.nonNewtonianPowerLaw = data

        specification = self._ui.transportSpec.currentData()
        if specification == TransportSpecification.POLYNOMIAL:
            self._dialog = PolynomialDialog(
                self, self.tr('Polynomial Viscosity'), self._transport.polynomial.viscosity.values)
            self._dialog.dataAccepted.connect(updatePolynomial)
        elif specification == TransportSpecification.CROSS_POWER_LAW:
            self._dialog = ViscosityCrossDialog(self, self._transport.crossPowerLaw)
            self._dialog.dataAccepted.connect(updateCrossPowerLaw)
        elif specification == TransportSpecification.HERSCHEL_BULKLEY:
            self._dialog = ViscosityHerschelBulkleyDialog(self, self._transport.herschelBulkley)
            self._dialog.dataAccepted.connect(updateHerschelBulkley)
        elif specification == TransportSpecification.BIRD_CARREAU:
            self._dialog = ViscosityCarreauDialog(self, self._transport.birdCarreau)
            self._dialog.dataAccepted.connect(updateBirdCarreau)
        elif specification == TransportSpecification.POWER_LAW:
            self._dialog = ViscosityNonNewtonianPowerLawDialog(self, self._transport.nonNewtonianPowerLaw)
            self._dialog.dataAccepted.connect(updateNonNewtonianPowerLaw)

        self._dialog.open()

    def _editThermalConductivity(self):
        def update(data: list[str]):
            self._transport.polynomial.thermalConductivity.values = data

        self._dialog = PolynomialDialog(
            self, self.tr('Polynomial Thermal Conductivity'), self._transport.polynomial.thermalConductivity.values)
        self._dialog.dataAccepted.connect(update)
        self._dialog.open()
