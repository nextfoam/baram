#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from .fan_dialog_ui import Ui_FanDialog
from .boundary_db import BoundaryDB


class FanDialog(QDialog):
    RELATIVE_PATH = '/fan'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FanDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getBoundaryXPath(bcid)

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_PATH

        writer = CoreDBWriter()
        writer.append(path + '/reverseDirection',
                      'true' if self._ui.reverseDirection.isChecked() else 'false', None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _connectSignalsSlots(self):
        self._ui.fanPQCurveFileSelect.clicked.connect(self._selectFanPQCurveFile)

    def _load(self):
        path = self._xpath + self.RELATIVE_PATH

        self._ui.reverseDirection.setChecked(self._db.getValue(path + '/reverseDirection') == 'true')

    def _selectFanPQCurveFile(self):
        fileName = QFileDialog.getOpenFileName(self, self.tr("Open CSV File"), "", self.tr("CSV (*.csv)"))
        if fileName[0]:
            self._ui.fanPQCurveFileName.setText(path.basename(fileName[0]))
