#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import Specification, Phase, DensitySpecification, ViscositySpecification
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

        self._setupSpecifications()

        self._connectSignalsSlots()
        self._load()

    def _load(self):
        db = coredb.CoreDB()
        self._name = MaterialDB.getName(self._mid)
        self._ui.name.setText(self._name)

        energyModelOn = ModelsDB.isEnergyModelOn()
        layout = self._ui.properties.layout()
        densitySpec = DensitySpecification.CONSTANT
        transportSpec = Specification.CONSTANT
        if energyModelOn:
            densitySpec = DensitySpecification(db.getValue(self._xpath + '/density/specification'))
            transportSpec = ViscositySpecification(db.getValue(self._xpath + '/viscosity/specification'))
            self._ui.specificHeatSpec.setCurrentText(
                MaterialDB.specificationToText(Specification(
                    db.getValue(self._xpath + '/specificHeat/specification'))))
        else:
            if TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR and self._phase == Phase.LIQUID:
                transportSpec = ViscositySpecification(db.getValue(self._xpath + '/viscosity/specification'))
            else:
                self._ui.transportSpec.setEnabled(False)
            self._ui.densitySpec.setEnabled(False)
            layout.setRowVisible(self._ui.specificHeatSpec, False)

        if energyModelOn or TurbulenceModelsDB.getModel() != TurbulenceModel.INVISCID:
            self._ui.transportSpec.setCurrentText(MaterialDB.specificationToText(transportSpec))
        else:
            layout.setRowVisible(self._ui.transportSpec, False)

        self._ui.densitySpec.setCurrentText(MaterialDB.specificationToText(densitySpec))
        self._ui.massDiffusivity.setText(db.getValue(self._xpath + '/mixture/massDiffusivity'))

        primarySpecie = db.getValue(self._xpath + '/mixture/primarySpecie')
        for mid, name in MaterialDB.getSpecies(self._mid).items():
            self._ui.primarySpecie.addItem(name, mid)
            if mid == primarySpecie:
                self._ui.primarySpecie.setCurrentText(name)

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name != self._name and MaterialDB.isMaterialExists(name):
            await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                self.tr(f'Material name "{name}" is already exists.'))
            return

        try:
            with coredb.CoreDB() as db:
                # Update Mixture
                db.setValue(self._xpath + '/name', name, self.tr("Name"))

                energyModelOn = ModelsDB.isEnergyModelOn()

                specifications = {}
                transportSpec = None
                specifications['/density/specification'] = self._ui.densitySpec.currentData()

                if energyModelOn:
                    specifications['/specificHeat/specification'] = self._ui.specificHeatSpec.currentData()

                if energyModelOn or TurbulenceModelsDB.getModel() != TurbulenceModel.INVISCID:
                    transportSpec = self._ui.transportSpec.currentData()
                    specifications['/viscosity/specification'] = transportSpec

                for subXPath, spec in specifications.items():
                    db.setValue(self._xpath + subXPath, spec.value)

                db.setValue(self._xpath + '/mixture/massDiffusivity',
                            self._ui.massDiffusivity.text(), self.tr("Mass Diffusivity"))
                db.setValue(self._xpath + '/mixture/primarySpecie', self._ui.primarySpecie.currentData())

                # Update Speicies
                if transportSpec and transportSpec != ViscositySpecification.SUTHERLAND:
                    specifications['/thermalConductivity/specification'] = (
                        Specification.CONSTANT if MaterialDB.isNonNewtonianSpecification(transportSpec)
                        else transportSpec)

                for mid in MaterialDB.getSpecies(self._mid):
                    xpath = MaterialDB.getXPath(mid)
                    for subXPath, spec in specifications.items():
                        db.setValue(xpath + subXPath, spec.value)

                self.accept()
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))
            return False

    def _setupSpecifications(self):
        if self._phase == Phase.GAS:
            self._setupSpecificationCombo(
                self._ui.densitySpec, [
                    DensitySpecification.CONSTANT,
                    DensitySpecification.POLYNOMIAL,
                    DensitySpecification.PERFECT_GAS,
                    DensitySpecification.INCOMPRESSIBLE_PERFECT_GAS,
                    # DensitySpecification.REAL_GAS_PENG_ROBINSON
                ]
            )
        else:
            self._setupSpecificationCombo(
                self._ui.densitySpec, [
                    DensitySpecification.CONSTANT,
                ]
            )

        self._setupSpecificationCombo(
            self._ui.specificHeatSpec, [
                Specification.CONSTANT,
                Specification.POLYNOMIAL
            ]
        )

        if self._phase != Phase.SOLID:
            if self._phase == Phase.LIQUID and TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR:
                self._setupSpecificationCombo(
                    self._ui.transportSpec, [
                        ViscositySpecification.CONSTANT,
                        ViscositySpecification.POLYNOMIAL,
                        ViscositySpecification.CROSS_POWER_LAW,
                        ViscositySpecification.HERSCHEL_BULKLEY,
                        ViscositySpecification.BIRD_CARREAU,
                        ViscositySpecification.POWER_LAW
                    ]
                )
            else:
                self._setupSpecificationCombo(
                    self._ui.transportSpec, [
                        ViscositySpecification.CONSTANT,
                        ViscositySpecification.SUTHERLAND,
                        ViscositySpecification.POLYNOMIAL,
                    ]
                )

    def _setupSpecificationCombo(self, combo, types):
        for t in types:
            combo.addItem(MaterialDB.specificationToText(t), t)

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
