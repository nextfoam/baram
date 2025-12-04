#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from typing import cast
import qasync

from PySide6.QtWidgets import QDialog, QFormLayout

from baramFlow.view.setup.materials.thermos_dialog import ThermosDialog
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.material.material import MaterialType, Phase, SpecificHeatSpecification, DensitySpecification, TransportSpecification
from baramFlow.case_manager import CaseManager
from baramFlow.base.material.database import materialsBase
from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from .mixture_dialog_ui import Ui_MixtureDialog


class MixtureDialog(QDialog):
    def __init__(self, parent, mid):
        super().__init__(parent)
        self._ui = Ui_MixtureDialog()
        self._ui.setupUi(self)

        self._mid = mid
        self._xpath = MaterialDB.getXPath(mid)
        self._name = None
        db = coredb.CoreDB()
        self._phase = Phase(db.getValue(self._xpath + '/phase'))

        energyOn = ModelsDB.isEnergyModelOn()

        layout = cast(QFormLayout, self._ui.properties.layout())

        layout.setRowVisible(self._ui.specificHeatSpec, energyOn)

        if (self._phase == Phase.SOLID and not energyOn) \
            or (self._phase != Phase.SOLID and TurbulenceModelsDB.getModel() == TurbulenceModel.INVISCID):
            layout.setRowVisible(self._ui.transportSpec, False)

        self._connectSignalsSlots()

        self._updateEnabled()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        self._name = MaterialDB.getName(self._mid)
        self._ui.name.setText(self._name)

        energyModelOn = ModelsDB.isEnergyModelOn()

        if energyModelOn:
            densitySpec = DensitySpecification(db.getValue(self._xpath + '/density/specification'))
        else:
            densitySpec = DensitySpecification.CONSTANT

        self._setupDensitySpec(densitySpec)

        if energyModelOn:
            specificHeatSpec = db.getValue(self._xpath + '/specificHeat/specification')
        else:
            specificHeatSpec = SpecificHeatSpecification.CONSTANT

        self._setupSpecificHeatSpec(specificHeatSpec)

        if energyModelOn or TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR:
            transportSpec = TransportSpecification(db.getValue(self._xpath + '/transport/specification'))
        else:
            transportSpec = TransportSpecification.CONSTANT

        self._setupTransportSpec(transportSpec)

        self._ui.massDiffusivity.setText(db.getValue(self._xpath + '/mixture/massDiffusivity'))

        primarySpecie = db.getValue(self._xpath + '/mixture/primarySpecie')
        for mid, name in MaterialDB.getSpecies(self._mid).items():
            self._ui.primarySpecie.addItem(name, mid)
            if mid == primarySpecie:
                self._ui.primarySpecie.setCurrentText(name)

    def _updateEnabled(self):
        caseManager = CaseManager()
        self._ui.dialogContents.setEnabled(not caseManager.isActive())
        self._ui.ok.setEnabled(not caseManager.isActive())

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name != self._name and MaterialDB.isMaterialExists(name):
            await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                self.tr(f'Material name "{name}" is already exists.'))
            return

        energyOn = ModelsDB.isEnergyModelOn()

        densitySpec = self._ui.densitySpec.currentData()

        if energyOn:  # specific heat is hidden if energer is turned off
            specificHeatSpec = self._ui.specificHeatSpec.currentData()
        else:
            specificHeatSpec = SpecificHeatSpecification.CONSTANT

        transportSpec = self._ui.transportSpec.currentData()

        if  not materialsBase.validateThermos(MaterialType.MIXTURE, self._phase, densitySpec, specificHeatSpec, transportSpec):
            highlights = (densitySpec, specificHeatSpec, transportSpec)
            dialog = ThermosDialog(MaterialType.MIXTURE, self._phase, highlights, self)

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
                # Update Mixture
                db.setValue(self._xpath + '/name', name, self.tr("Name"))

                specifications = {}
                transportSpec = None
                specifications['/density/specification'] = self._ui.densitySpec.currentData()

                if energyOn:
                    specifications['/specificHeat/specification'] = self._ui.specificHeatSpec.currentData()

                if energyOn or TurbulenceModelsDB.getModel() != TurbulenceModel.INVISCID:
                    transportSpec = self._ui.transportSpec.currentData()
                    specifications['/transport/specification'] = transportSpec

                for subXPath, spec in specifications.items():
                    db.setValue(self._xpath + subXPath, spec.value)

                db.setValue(self._xpath + '/mixture/massDiffusivity',
                            self._ui.massDiffusivity.text(), self.tr("Mass Diffusivity"))
                db.setValue(self._xpath + '/mixture/primarySpecie', self._ui.primarySpecie.currentData())

                # Update Speicies
                for mid in MaterialDB.getSpecies(self._mid):
                    xpath = MaterialDB.getXPath(mid)
                    for subXPath, spec in specifications.items():
                        db.setValue(xpath + subXPath, spec.value)

                self.accept()
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))
            return False

    def _setupDensitySpec(self, spec):
        self._ui.densitySpec.clear()

        densitySpecs = MaterialDB.availableDensitySpec(MaterialType.MIXTURE, self._phase)

        texts = [MaterialDB.densitySpecToText(s) for s in densitySpecs]
        self._ui.densitySpec.setup(texts, densitySpecs, spec)

    def _setupSpecificHeatSpec(self, spec):

        self._ui.specificHeatSpec.clear()

        specificHeatSpecs = MaterialDB.availableSpecificHeatSpecs(MaterialType.MIXTURE, self._phase)

        texts = [MaterialDB.specificHeatSpecToText(s) for s in specificHeatSpecs]
        self._ui.specificHeatSpec.setup(texts, specificHeatSpecs, spec)

    def _setupTransportSpec(self, spec):
        self._ui.transportSpec.clear()

        transportSpecs = MaterialDB.availableTransportSpecs(MaterialType.MIXTURE, self._phase)

        texts = [MaterialDB.transportSpecToText(s) for s in transportSpecs]
        self._ui.transportSpec.setup(texts, transportSpecs, spec)
