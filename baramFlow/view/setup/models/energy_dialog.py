#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.general_db import GeneralDB
from widgets.async_message_box import AsyncMessageBox
from .energy_dialog_ui import Ui_EnergyDialog


class EnergyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_EnergyDialog()
        self._ui.setupUi(self)

        if GeneralDB.isCompressible() or ModelsDB.isMultiphaseModelOn():
            self._ui.include.setEnabled(False)
            self._ui.notInclude.setEnabled(False)
        else:
            self._ui.include.setEnabled(True)
            self._ui.notInclude.setEnabled(True)

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

    def _load(self):
        if ModelsDB.isEnergyModelOn():
            self._ui.include.setChecked(True)
        else:
            self._ui.notInclude.setChecked(True)
