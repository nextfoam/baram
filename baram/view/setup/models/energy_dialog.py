#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baram.coredb.coredb_writer import CoreDBWriter
from baram.coredb.models_db import ModelsDB
from baram.coredb.general_db import GeneralDB
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

    def accept(self):
        writer = CoreDBWriter()
        writer.append(ModelsDB.ENERGY_MODELS_XPATH, 'on' if self._ui.include.isChecked() else 'off', None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        if ModelsDB.isEnergyModelOn():
            self._ui.include.setChecked(True)
        else:
            self._ui.notInclude.setChecked(True)
