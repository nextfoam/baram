#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.specie_model_db import SpecieModelDB
from .species_dialog_ui import Ui_SpeciesDialog


class SpeciesDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_SpeciesDialog()
        self._ui.setupUi(self)

        self._originSetting = None

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        include = self._ui.include.isChecked()
        if self._originSetting == include:
            self.close()
            return

        try:
            with coredb.CoreDB() as db:
                if include:
                    SpecieModelDB.turnOn(db)
                else:
                    SpecieModelDB.turnOff(db)

            self.accept()
        except ConfigurationException as ex:
            await AsyncMessageBox().information(self, self.tr('Model Change Failed'), str(ex))

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        self._originSetting = ModelsDB.isSpeciesModelOn()
        if self._originSetting:
            self._ui.include.setChecked(True)
        else:
            self._ui.notInclude.setChecked(True)
