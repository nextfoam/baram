#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.models_db import ModelsDB
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

        if not include:
            db = coredb.CoreDB()
            for mid, name, _, _ in db.getMaterials('mixture'):
                if db.isMaterialRefereced(mid):
                    await AsyncMessageBox().information(
                        self, self.tr('Input Error'),
                        self.tr(
                            'Mixture material "{}" is referenced by other configurations.'
                            'It should be cleared to turn off Species model.').format(name))
                    return

        writer = CoreDBWriter()
        writer.append(ModelsDB.SPECIES_MODELS_XPATH, 'on' if self._ui.include.isChecked() else 'off', None)

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().critical(self, self.tr("Input Error"), writer.firstError().toMessage())
            return

        self.accept()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        self._originSetting = ModelsDB.isSpeciesModelOn()
        if self._originSetting:
            self._ui.include.setChecked(True)
        else:
            self._ui.notInclude.setChecked(True)
