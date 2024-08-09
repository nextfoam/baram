#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.material_db import MaterialDB, Specification, Phase
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
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
        if energyModelOn:
            densitySpec = db.getValue(self._xpath + '/density/specification')
            transportSpec = db.getValue(self._xpath + '/viscosity/specification')
            self._ui.specificHeatSpec.setCurrentText(
                MaterialDB.dbSpecificationToText(db.getValue(self._xpath + '/specificHeat/specification')))
        else:
            densitySpec = Specification.CONSTANT.value
            transportSpec = Specification.CONSTANT.value
            self._ui.densitySpec.setEnabled(False)
            self._ui.transportSpec.setEnabled(False)
            layout.setRowVisible(self._ui.specificHeatSpec, False)

        if energyModelOn or ModelsDB.getTurbulenceModel() != TurbulenceModel.INVISCID:
            self._ui.transportSpec.setCurrentText(MaterialDB.dbSpecificationToText(transportSpec))
        else:
            layout.setRowVisible(self._ui.transportSpec, False)

        self._ui.densitySpec.setCurrentText(MaterialDB.dbSpecificationToText(densitySpec))
        self._ui.massDiffusivity.setText(db.getValue(self._xpath + '/mixture/massDiffusivity'))

        primarySpecie = int(db.getValue(self._xpath + '/mixture/primarySpecie'))
        for mid, name in MaterialDB.getSpecies(self._mid).items():
            self._ui.primarySpecie.addItem(name, str(mid))
            if mid == primarySpecie:
                self._ui.primarySpecie.setCurrentText(name)

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name != self._name and MaterialDB.isMaterialExists(name):
            await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                self.tr(f'Material name "{name}" is already exists.'))
            return

        writer = CoreDBWriter()
        energyModelOn = ModelsDB.isEnergyModelOn()

        writer.append(self._xpath + '/name', name, self.tr("Name"))

        writer.append(self._xpath + '/density/specification', self._ui.densitySpec.currentData().value, None)

        if ModelsDB.isEnergyModelOn():
            writer.append(self._xpath + '/specificHeat/specification',
                          self._ui.specificHeatSpec.currentData().value, None)

        if energyModelOn or ModelsDB.getTurbulenceModel() != TurbulenceModel.INVISCID:
            writer.append(self._xpath + '/viscosity/specification', self._ui.transportSpec.currentData().value, None)

        writer.append(self._xpath + '/mixture/massDiffusivity',
                      self._ui.massDiffusivity.text(), self.tr("Mass Diffusivity"))
        writer.append(self._xpath + '/mixture/primarySpecie',
                      self._ui.primarySpecie.currentData(), self.tr("Mass Diffusivity"))

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.accept()

    def _setupSpecifications(self):
        if self._phase == Phase.GAS:
            self._setupSpecificationCombo(
                self._ui.densitySpec, [
                    Specification.CONSTANT,
                    Specification.POLYNOMIAL,
                    Specification.PERFECT_GAS,
                    Specification.INCOMPRESSIBLE_PERFECT_GAS,
                    # Specification.REAL_GAS_PENG_ROBINSON
                ]
            )
        else:
            self._setupSpecificationCombo(
                self._ui.densitySpec, [
                    Specification.CONSTANT,
                ]
            )

        self._setupSpecificationCombo(
            self._ui.specificHeatSpec, [
                Specification.CONSTANT,
                Specification.POLYNOMIAL
            ]
        )

        if self._phase == Phase.GAS:
            self._setupSpecificationCombo(
                self._ui.transportSpec, [
                    Specification.CONSTANT,
                    Specification.SUTHERLAND,
                    Specification.POLYNOMIAL
                ]
            )
        elif self._phase == Phase.LIQUID:
            self._setupSpecificationCombo(
                self._ui.transportSpec, [
                    Specification.CONSTANT,
                    Specification.POLYNOMIAL
                ]
            )

    def _setupSpecificationCombo(self, combo, types):
        for t in types:
            combo.addItem(MaterialDB.specificationToText(t), t)

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
