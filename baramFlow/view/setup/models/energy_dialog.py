#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.base.model.model import DPMParticleType
from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.region_db import RegionDB
from widgets.async_message_box import AsyncMessageBox
from .energy_dialog_ui import Ui_EnergyDialog


class EnergyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_EnergyDialog()
        self._ui.setupUi(self)

        self._includeDeniedMessage = None
        self._notIncludeDeniedMessage = None

        if ModelsDB.isMultiphaseModelOn():
            self._includeDeniedMessage = self.tr('Energy Model is unavailable in Multiphase model.')

        if GeneralDB.isCompressible():
            self._notIncludeDeniedMessage = self.tr('Energy Model must be included in Compressible model.')
        elif DPMModelManager.isModelOn() and DPMModelManager.particleType() == DPMParticleType.DROPLET:
            self._notIncludeDeniedMessage = self.tr('Energy Model must be included when DPM Model is active.')
        elif RegionDB.isMultiRegion():
            self._notIncludeDeniedMessage = self.tr('Energy Model must be included in Multi-region mode.')

        self._connectSignalsSlots()

        self._load()

    @qasync.asyncSlot()
    async def accept(self):
        coredb.CoreDB().setValue(ModelsDB.ENERGY_MODELS_XPATH, 'on' if self._ui.include.isChecked() else 'off')

        super().accept()

        if not self._ui.include.isChecked():
            await AsyncMessageBox().information(
                self, self.tr('Warning'),
                self.tr('Available material properties or specifications might have changed. '
                        'Please confirm the property values before continuing.'))

    def _connectSignalsSlots(self):
        if self._includeDeniedMessage is not None:
            self._ui.include.clicked.connect(self._denyInclude)

        if self._notIncludeDeniedMessage is not None:
            self._ui.notInclude.clicked.connect(self._denyNotInclude)

    def _load(self):
        if ModelsDB.isEnergyModelOn():
            self._ui.include.setChecked(True)
        else:
            self._ui.notInclude.setChecked(True)

    @qasync.asyncSlot()
    async def _denyInclude(self):
        self._ui.notInclude.setChecked(True)
        await AsyncMessageBox().information(self, self.tr('Input Error'), self._includeDeniedMessage)

    @qasync.asyncSlot()
    async def _denyNotInclude(self):
        self._ui.include.setChecked(True)
        await AsyncMessageBox().information(self, self.tr('Input Error'), self._notIncludeDeniedMessage)