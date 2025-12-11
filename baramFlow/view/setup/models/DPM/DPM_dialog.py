#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QTimer
import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.coredb.general_db import GeneralDB
from widgets.async_message_box import AsyncMessageBox
from widgets.enum_button_group import EnumButtonGroup
from widgets.selector_dialog import SelectorDialog, SelectorItem

from baramFlow.base.material.material import MaterialManager, MaterialType, Materials, Phase
from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.base.model.model import DPMParticleType, DPMTrackingScheme, DPMDragForce, DPMLiftForce, Contamination
from baramFlow.base.model.model import DPMTurbulentDispersion, DPMHeatTransferSpeicification
from baramFlow.base.model.model import DPMEvaporationModel, DPMEnthalpyTransferType
from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModelsDB, TurbulenceModel
from .DPM_dialog_ui import Ui_DPMdialog
from .injection_list_dialog import InjectionListDialog
from .droplet_compsition_list import DropletCompositionList


def _getAvailableDropletLiquids(materials: Materials):
    availableDropletLiquids: list[tuple[str, str]] = []  # list of (<mid>, <name>)

    for mid, name in RegionDB.getMixturesInRegions():
        if MaterialDB.getPhase(mid) == Phase.GAS:
            break  # support only one mixture for now
    else:
        return availableDropletLiquids

    species: list[str] = []
    for specie, _ in MaterialDB.getSpecies(mid).items():
        chemicalFormula = MaterialDB.getChemicalFormula(specie)
        species.append(chemicalFormula)

    for liquid in materials.getMaterials(types=[MaterialType.NONMIXTURE], phases=[Phase.LIQUID]):
        chemicalFormula = MaterialDB.getChemicalFormula(liquid.mid)
        if chemicalFormula in species:
            availableDropletLiquids.append((liquid.mid, liquid.name))

    return availableDropletLiquids


class DPMDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_DPMdialog()
        self._ui.setupUi(self)

        self._particleTypeRadios = EnumButtonGroup()
        self._dropletComposition = None
        self._dragForceRadios = EnumButtonGroup()
        self._contaminationRadios = EnumButtonGroup()
        self._liftForceRadios = EnumButtonGroup()
        self._turbulentDispersionRadios = EnumButtonGroup()
        self._heatTransferRadios = EnumButtonGroup()
        self._evaporationModelRadios = EnumButtonGroup()
        self._enthalpyTransferTypeRadios = EnumButtonGroup()

        self._heatTransferTabIndex = self._ui.tabWidget.indexOf(self._ui.heatTransfreTab)
        self._evaporationTabIndex = self._ui.tabWidget.indexOf(self._ui.evaporationTab)

        self._properties = None
        self._injections = None

        self._particleType = None
        self._inertParticle = None
        self._coreMaterials = MaterialManager.loadMaterials()
        self._selectableParticles = []
        self._turbulentDispersion = None

        self._dialog = None

        self._particleTypeRadios.addEnumButton(self._ui.none, DPMParticleType.NONE)
        self._particleTypeRadios.addEnumButton(self._ui.inertButton, DPMParticleType.INERT)
        self._particleTypeRadios.addEnumButton(self._ui.dropletButton, DPMParticleType.DROPLET)
        self._particleTypeRadios.addEnumButton(self._ui.combustingButton, DPMParticleType.COMBUSTING)

        self._ui.trackingScheme.addItem(self.tr('Implicit'),    DPMTrackingScheme.IMPLICIT)
        self._ui.trackingScheme.addItem(self.tr('Analytic'),    DPMTrackingScheme.ANALYTIC)

        self._dragForceRadios.addEnumButton(self._ui.dragForceSpherical,            DPMDragForce.SPHERICAL)
        self._dragForceRadios.addEnumButton(self._ui.dragForceNonSpherical,         DPMDragForce.NON_SPHERICAL)
        self._dragForceRadios.addEnumButton(self._ui.dragForceDistortedSphere,      DPMDragForce.DISTORTED_SPHERE)
        self._dragForceRadios.addEnumButton(self._ui.dragForceWenAndYu,             DPMDragForce.WEN_AND_YU)
        self._dragForceRadios.addEnumButton(self._ui.dragForceGidaspow,             DPMDragForce.GIDASPOW)
        self._dragForceRadios.addEnumButton(self._ui.dragForceDuPlesisAndMailyah,   DPMDragForce.DU_PIESSIS_AND_MASLIYAH)
        self._dragForceRadios.addEnumButton(self._ui.dragForceTomiyama,             DPMDragForce.TOMIYAMA)

        self._contaminationRadios.addEnumButton(self._ui.noContamination,       Contamination.NO_CONTAMINATION)
        self._contaminationRadios.addEnumButton(self._ui.slightContamination,   Contamination.SLIGHT_CONTAMINATION)
        self._contaminationRadios.addEnumButton(self._ui.fullContamination,     Contamination.FULL_CONTAMINATION)

        self._liftForceRadios.addEnumButton(self._ui.liftForceNone,         DPMLiftForce.NONE)
        self._liftForceRadios.addEnumButton(self._ui.liftForceSaffmanMei,   DPMLiftForce.SAFFMAN_MEI)
        self._liftForceRadios.addEnumButton(self._ui.liftForceTomiyama,     DPMLiftForce.TOMIYAMA)

        self._turbulentDispersionRadios.addEnumButton(self._ui.noneDispersion,
                                                      DPMTurbulentDispersion.NONE)
        self._turbulentDispersionRadios.addEnumButton(self._ui.stochasticDispersion,
                                                      DPMTurbulentDispersion.STOCHASTIC_DISPERSION)
        self._turbulentDispersionRadios.addEnumButton(self._ui.gradientDispersion,
                                                      DPMTurbulentDispersion.GRADIENT_DISPERSION)

        self._heatTransferRadios.addEnumButton(self._ui.heatTransferNone,
                                               DPMHeatTransferSpeicification.NONE)
        self._heatTransferRadios.addEnumButton(self._ui.heatTransferRanzMarshall,
                                               DPMHeatTransferSpeicification.RANZ_MARHALL)

        self._evaporationModelRadios.addEnumButton(self._ui.evaporationNone,
                                                   DPMEvaporationModel.NONE)
        self._evaporationModelRadios.addEnumButton(self._ui.evaporationDiffusionControlled,
                                                   DPMEvaporationModel.DIFFUSION_CONTROLLED)
        self._evaporationModelRadios.addEnumButton(self._ui.evaporationConvectionDdiffusionControlled,
                                                   DPMEvaporationModel.CONVECTION_DIFFUSION_CONTROLLED)

        self._enthalpyTransferTypeRadios.addEnumButton(self._ui.enthalpyDiference,
                                                       DPMEnthalpyTransferType.ENTHALPY_DIFFENENCE)
        self._enthalpyTransferTypeRadios.addEnumButton(self._ui.latetHeat,
                                                       DPMEnthalpyTransferType.LATENT_HEAT)

        transient = GeneralDB.isTimeTransient()
        energyOn = ModelsDB.isEnergyModelOn()

        isLaminar = (TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR)


        selectableSolids = []

        particles = self._coreMaterials.getMaterials(phases=[Phase.SOLID, Phase.LIQUID])
        for m in particles:
            self._selectableParticles.append(SelectorItem(m.name, m.name, (m.mid, m.name)))

            if m.phase == Phase.SOLID:
                selectableSolids.append(SelectorItem(m.name, m.name, (m.mid, m.name)))

        selectableDropletLiquids = [SelectorItem(name, name, (mid, name)) for mid, name in _getAvailableDropletLiquids(self._coreMaterials)]

        self._dropletComposition = DropletCompositionList(self, self._ui.composition, selectableSolids, selectableDropletLiquids)


        self._ui.inertButton.setEnabled(not ModelsDB.isMultiphaseModelOn()
                                        and not RegionDB.isMultiRegion()
                                        and len(self._selectableParticles) > 0)

        self._ui.dropletButton.setEnabled(not ModelsDB.isMultiphaseModelOn()
                                        and not RegionDB.isMultiRegion()
                                        and energyOn
                                        and len(selectableDropletLiquids) > 0)

        if len(self._selectableParticles) > 0:
            self._setInertParticle(particles[0].mid, particles[0].name)


        self._ui.combustingButton.hide()  # Combusting not supported yet

        self._ui.dropletGroup.hide()

        self._ui.temperatureWidget.setVisible(energyOn)

        self._ui.maxParticleCourantNumberWidget.setVisible(transient)
        self._ui.DPMIterationIntervalWidget.setVisible(not transient)
        
        self._ui.tabWidget.setTabEnabled(self._heatTransferTabIndex, energyOn)

        #
        # Temporary hiding until MPPICFoam is added
        # Begin

        self._ui.dragForceDistortedSphere.hide()
        self._ui.dragForceWenAndYu.hide()
        self._ui.dragForceGidaspow.hide()
        self._ui.dragForceDuPlesisAndMailyah.hide()
        self._ui.dragForceTomiyama.hide()
        self._ui.dragForceTomiyamaParams.hide()

        self._ui.liftForceTomiyama.hide()
        self._ui.liftForceTomiyamaParams.hide()

        # End

        self._ui.brownianMotionForce.setEnabled(isLaminar and energyOn)

        self._connectSignalsSlots()

        self._load()

    def add(self, mid):
        pass

    def _connectSignalsSlots(self):
        self._particleTypeRadios.dataChecked.connect(self._particleTypeChanged)
        self._ui.inertParticleChange.clicked.connect(self._openParticleSelector)
        self._dropletComposition.changed.connect(self._updateDropletTotalComposition)
        self._ui.injections.clicked.connect(self._openInjectionListDialog)
        self._dragForceRadios.dataChecked.connect(self._dragForceChanged)
        self._liftForceRadios.dataChecked.connect(self._liftForceChanged)
        self._turbulentDispersionRadios.dataChecked.connect(self._turbulentDispersionChanged)
        self._heatTransferRadios.dataChecked.connect(self._heatTransferChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        turbulenceModel = TurbulenceModelsDB.getModel()
        energyOn = ModelsDB.isEnergyModelOn()

        self._properties = DPMModelManager.properties()
        self._particleType = self._properties.particleType

        self._particleTypeRadios.setCheckedData(self._particleType)

        mid = self._properties.inert.inertParticle
        if mid != '0':
            self._setInertParticle(mid, self._coreMaterials.getMaterial(mid).name)

        for c in self._properties.droplet.composition:
            material = self._coreMaterials.getMaterial(c.mid)
            if material.phase == Phase.SOLID:
                self._dropletComposition.addSolid((c.mid, material.name), c.composition)
            elif material.phase == Phase.LIQUID:
                self._dropletComposition.addLiquid((c.mid, material.name), c.composition)

        self._updateDropletTotalComposition()
        self._ui.temperature.setBatchableNumber(self._properties.droplet.temperature)

        self._ui.interactionWithContinuousPhase.setChecked(
            self._properties.numericalConditions.interactionWithContinuousPhase)
        self._ui.maxParticleCourantNumber.setBatchableNumber(
            self._properties.numericalConditions.maxParticleCourantNumber)
        self._ui.DPMIterationInterval.setBatchableNumber(
            self._properties.numericalConditions.DPMIterationInterval)
        self._ui.nodeBasedAveraging.setChecked(self._properties.numericalConditions.nodeBasedAveraging)
        self._ui.trackingScheme.setCurrentIndex(
            self._ui.trackingScheme.findData(self._properties.numericalConditions.trackingScheme))

        self._dragForceRadios.setCheckedData(self._properties.kinematicModel.dragForce.specification)
        self._ui.shapeFactor.setBatchableNumber(
            self._properties.kinematicModel.dragForce.nonSphereDrag.shapeFactor)
        self._ui.dragTomiyamaSurfaceTension.setBatchableNumber(
            self._properties.kinematicModel.dragForce.tomyamaDrag.surfaceTension)
        self._contaminationRadios.setCheckedData(self._properties.kinematicModel.dragForce.tomyamaDrag.contamination)
        self._liftForceRadios.setCheckedData(self._properties.kinematicModel.liftForce.specification)
        self._ui.liftTomiyamaSurfaceTension.setBatchableNumber(
            self._properties.kinematicModel.liftForce.tomiyamaLift.surfaceTension)
        self._ui.gravity.setChecked(self._properties.kinematicModel.gravity)
        self._ui.pressureGradient.setChecked(self._properties.kinematicModel.pressureGradient)

        if energyOn and turbulenceModel == TurbulenceModel.LAMINAR:
            self._ui.brownianMotionForce.setChecked(not self._properties.kinematicModel.brownianMotionForce.disabled)

        self._ui.molecularFreePathLength.setBatchableNumber(
            self._properties.kinematicModel.brownianMotionForce.molecularFreePathLength)

        self._ui.useTurtulence.setChecked(self._properties.kinematicModel.brownianMotionForce.useTurbulence)

        self._turbulentDispersion = (
            DPMTurbulentDispersion.NONE if turbulenceModel == TurbulenceModel.SPALART_ALLMARAS
            else self._properties.turbulentDispersion)

        self._turbulentDispersionRadios.setCheckedData(self._turbulentDispersion)
        self._heatTransferRadios.setCheckedData(self._properties.heatTransfer.specification)
        self._ui.birdCorrection.setChecked(self._properties.heatTransfer.ranzMarsahll.birdCorrection)

        self._evaporationModelRadios.setCheckedData(self._properties.evaporation.model)
        self._enthalpyTransferTypeRadios.setCheckedData(self._properties.evaporation.enthalpyTransferType)

    @qasync.asyncSlot()
    async def _accept(self):
        dragForce = self._dragForceRadios.checkedData()
        liftForce = self._liftForceRadios.checkedData()
        brownianMotionForceChecked = self._ui.brownianMotionForce.isChecked()

        if self._particleType != DPMParticleType.NONE:
            try:
                self._ui.maxParticleCourantNumber.validate(self.tr('Max. Particle Courant Number'),low=0,
                                                           lowInclusive=False)
                self._ui.DPMIterationInterval.validate(self.tr('DPM Iteration Interval'),low=0,
                                                           lowInclusive=False)

                if dragForce == DPMDragForce.NON_SPHERICAL:
                    self._ui.shapeFactor.validate(self.tr('Shape Factor'), low=0, high=1, lowInclusive=False)
                elif dragForce == DPMDragForce.TOMIYAMA:
                    self._ui.dragTomiyamaSurfaceTension.validate(self.tr('Surface Tension'), low=0)

                if liftForce == DPMLiftForce.TOMIYAMA:
                    self._ui.liftTomiyamaSurfaceTension.validate(self.tr('Surface Tension'), low=0)

                if brownianMotionForceChecked:
                    self._ui.molecularFreePathLength.validate(self.tr('Molecular Free Path Length'), low=0)

                if self._particleType == DPMParticleType.INERT:
                    if self._inertParticle == '0':
                        await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                            self.tr('Select Inert Particle.'))
                        return
                elif self._particleType == DPMParticleType.DROPLET:
                    if not self._dropletComposition.hasLiquids():
                        await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                            self.tr('Add at least one liquid to the Composition.'))
                        return

                    if float(self._ui.totalComposition.text()) != 1:
                        await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                            self.tr('Total Composition must be 1.'))
                        return
                    self._ui.temperature.validate(self.tr('Temperature'))
            except ValueError as e:
                await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
                return

        self._properties.particleType = self._particleType
        if self._particleType != DPMParticleType.NONE:
            if self._particleType == DPMParticleType.INERT:
                self._properties.inert.inertParticle = self._inertParticle
            elif self._particleType == DPMParticleType.DROPLET:
                self._properties.droplet.composition = self._dropletComposition.data()
                self._properties.droplet.temperature = self._ui.temperature.batchableNumber()

            self._properties.numericalConditions.interactionWithContinuousPhase = self._ui.interactionWithContinuousPhase.isChecked()
            self._properties.numericalConditions.maxParticleCourantNumber = self._ui.maxParticleCourantNumber.batchableNumber()
            self._properties.numericalConditions.DPMIterationInterval = self._ui.DPMIterationInterval.batchableNumber()
            self._properties.numericalConditions.nodeBasedAveraging = self._ui.nodeBasedAveraging.isChecked()
            self._properties.numericalConditions.trackingScheme = self._ui.trackingScheme.currentData()

            self._properties.kinematicModel.dragForce.specification = dragForce
            if dragForce == DPMDragForce.NON_SPHERICAL:
                self._properties.kinematicModel.dragForce.nonSphereDrag.shapeFactor = self._ui.shapeFactor.batchableNumber()
            elif dragForce == DPMDragForce.TOMIYAMA:
                self._properties.kinematicModel.dragForce.tomyamaDrag.surfaceTension = self._ui.dragTomiyamaSurfaceTension.batchableNumber()
                self._properties.kinematicModel.dragForce.tomyamaDrag.contamination = self._contaminationRadios.checkedData()

            self._properties.kinematicModel.liftForce.specification = liftForce
            if liftForce == DPMLiftForce.TOMIYAMA:
                self._properties.kinematicModel.liftForce.tomiyamaLift.surfaceTension = self._ui.liftTomiyamaSurfaceTension.batchableNumber()

            self._properties.kinematicModel.gravity = self._ui.gravity.isChecked()
            self._properties.kinematicModel.pressureGradient = self._ui.pressureGradient.isChecked()
            self._properties.kinematicModel.brownianMotionForce.disabled = not brownianMotionForceChecked
            if brownianMotionForceChecked:
                self._properties.kinematicModel.brownianMotionForce.molecularFreePathLength = self._ui.molecularFreePathLength.batchableNumber()
                self._properties.kinematicModel.brownianMotionForce.useTurbulence = self._ui.useTurtulence.isChecked()

            self._properties.turbulentDispersion = self._turbulentDispersion

            if self._particleType == DPMParticleType.DROPLET:
                heatTransfer = self._heatTransferRadios.checkedData()
                self._properties.heatTransfer.specification = heatTransfer
                if heatTransfer == DPMHeatTransferSpeicification.RANZ_MARHALL:
                    self._properties.heatTransfer.ranzMarsahll.birdCorrection = self._ui.birdCorrection.isChecked()

                self._properties.evaporation.model = self._evaporationModelRadios.checkedData()
                self._properties.evaporation.enthalpyTransferType = self._enthalpyTransferTypeRadios.checkedData()

        with coredb.CoreDB() as db:
            DPMModelManager.updateDPMModel(db, self._properties, self._injections)

        self.accept()

    @qasync.asyncSlot()
    async def _particleTypeChanged(self):
        type_ = self._particleTypeRadios.checkedData()

        self._particleType = type_
        if type_ == DPMParticleType.NONE:
            self._ui.properties.setEnabled(False)
            self._ui.tabWidget.setEnabled(False)

            return

        if type_ == DPMParticleType.INERT:
            self._ui.inertParticleGroup.setVisible(True)
            self._ui.dropletGroup.setVisible(False)
            self._ui.tabWidget.setTabEnabled(self._evaporationTabIndex, False)
        elif type_ == DPMParticleType.DROPLET:
            self._ui.inertParticleGroup.setVisible(False)
            self._ui.dropletGroup.setVisible(True)
            self._ui.tabWidget.setTabEnabled(self._evaporationTabIndex, True)

        self._ui.properties.setEnabled(True)
        self._ui.tabWidget.setEnabled(True)

        QTimer.singleShot(0, self.adjustSize)

    def _dragForceChanged(self, dragForce):
        self._ui.shapeFactor.setEnabled(dragForce == DPMDragForce.NON_SPHERICAL)
        self._ui.dragForceTomiyamaParams.setEnabled(dragForce == DPMDragForce.TOMIYAMA)

    def _liftForceChanged(self, liftForce):
        self._ui.liftForceTomiyamaParams.setEnabled(liftForce == DPMLiftForce.TOMIYAMA)

    @qasync.asyncSlot()
    async def _turbulentDispersionChanged(self, dispersion):
        if (dispersion != DPMTurbulentDispersion.NONE
                and TurbulenceModelsDB().getModel() == TurbulenceModel.SPALART_ALLMARAS):
            self._turbulentDispersionRadios.setCheckedData(self._turbulentDispersion)
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('Turbulent dispersion of particles cannot be included'
                        ' if the Spalart-Allmaras turbulence model is used.'))
        else:
            self._turbulentDispersion = dispersion

    def _heatTransferChanged(self, heatTransfer):
        self._ui.birdCorrection.setEnabled(heatTransfer == DPMHeatTransferSpeicification.RANZ_MARHALL)

    def _openParticleSelector(self):
        def addSolids():
            mid, name = self._dialog.selectedItem()
            self._setInertParticle(mid, name)

        self._dialog = SelectorDialog(self, self.tr("Select Material"), self.tr("Select Material"),
                                      self._selectableParticles)
        self._dialog.accepted.connect(addSolids)
        self._dialog.open()

    def _updateDropletTotalComposition(self):
        total = self._dropletComposition.total()
        self._ui.totalComposition.setText(str(total))
        self._ui.totalComposition.setStyleSheet('' if total == 1 else 'color: red;')

    def _openInjectionListDialog(self):
        self._dialog = InjectionListDialog(
            self, DPMModelManager.injections() if self._injections is None else self._injections)
        self._dialog.accepted.connect(self._updateInjections)
        self._dialog.open()

    def _updateInjections(self):
        self._injections = self._dialog.injections()

    def _setInertParticle(self, mid, name):
        self._inertParticle = mid
        self._ui.inertParticle.setText(name)
