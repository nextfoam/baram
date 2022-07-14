#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.boundary_db import BoundaryDB
from .subsonic_outflow_dialog_ui import Ui_SubsonicOutflowDialog


class SubsonicOutflowDialog(QDialog):
    RELATIVE_XPATH = '/subsonicOutflow'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_SubsonicOutflowDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/staticPressure', self._ui.pressure.text(), self.tr("Pressure"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.pressure.setText(self._db.getValue(path + '/staticPressure'))
