#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QMessageBox

from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.models_db import ModelsDB
from .species_dialog_ui import Ui_SpeciesDialog


class SpeciesDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_SpeciesDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        writer = CoreDBWriter()
        writer.append(ModelsDB.SPECIES_MODELS_XPATH, 'on' if self._ui.include.isChecked() else 'off', None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.accept()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        if ModelsDB.isSpeciesModelOn():
            self._ui.include.setChecked(True)
        else:
            self._ui.notInclude.setChecked(True)
