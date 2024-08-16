#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.general_db import GeneralDB
from .operating_conditions_dialog_ui import Ui_OperatingConditionsDialog


class OperatingConditionsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_OperatingConditionsDialog()
        self._ui.setupUi(self)

        self._xpath = GeneralDB.OPERATING_CONDITIONS_XPATH
        self._load()

    def accept(self):
        writer = CoreDBWriter()
        writer.append(self._xpath + '/pressure', self._ui.operationPressure.text(), self.tr("Operating Pressure"))
        writer.append(self._xpath + '/referencePressureLocation/x',
                      self._ui.referencePressureLocationX.text(), self.tr("Refeerence Pressure Location X"))
        writer.append(self._xpath + '/referencePressureLocation/y',
                      self._ui.referencePressureLocationY.text(), self.tr("Refeerence Pressure Location Y"))
        writer.append(self._xpath + '/referencePressureLocation/z',
                      self._ui.referencePressureLocationZ.text(), self.tr("Refeerence Pressure Location Z"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        db = coredb.CoreDB()
        self._ui.operationPressure.setText(db.getValue(self._xpath + '/pressure'))
        self._ui.referencePressureLocationX.setText(db.getValue(self._xpath + '/referencePressureLocation/x'))
        self._ui.referencePressureLocationY.setText(db.getValue(self._xpath + '/referencePressureLocation/y'))
        self._ui.referencePressureLocationZ.setText(db.getValue(self._xpath + '/referencePressureLocation/z'))
