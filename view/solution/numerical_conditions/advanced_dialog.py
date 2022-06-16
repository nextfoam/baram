#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from .advanced_dialog_ui import Ui_AdvancedDialog
from .numerical_db import NumericalDB


class AdvancedDialog(QDialog):
    RELATIVE_PATH = '/advanced'

    def __init__(self):
        super().__init__()
        self._ui = Ui_AdvancedDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = NumericalDB.NUMERICAL_CONDITIONS_XPATH + self.RELATIVE_PATH

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        self._ui.minimumStaticTemperature.setText(self._db.getValue(self._xpath + '/limits/minimumStaticTemperature'))
        self._ui.maximumStaticTemperature.setText(self._db.getValue(self._xpath + '/limits/maximumStaticTemperature'))

        return super().showEvent(ev)

    def accept(self):
        writer = CoreDBWriter()
        writer.append(self._xpath + '/limits/minimumStaticTemperature', self._ui.minimumStaticTemperature.text(), self.tr("Minimum Static Temperature"))
        writer.append(self._xpath + '/limits/maximumStaticTemperature', self._ui.maximumStaticTemperature.text(), self.tr("Maximum Static Temperature"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()
