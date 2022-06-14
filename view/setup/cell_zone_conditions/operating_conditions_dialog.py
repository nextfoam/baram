#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from .operating_conditions_dialog_ui import Ui_OperatingConditionsDialog


class OperatingConditionsDialog(QDialog):
    OPERATING_CONDITIONS_XPATH = './/operatingConditions'

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_OperatingConditionsDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._load()

    def accept(self):
        path = self.OPERATING_CONDITIONS_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/pressure', self._ui.operationPressure.text(), self.tr("Operating Pressure"))
        writer.append(path + '/referencePressureLocation/x',
                      self._ui.referencePressureLocationX.text(), self.tr("Refeerence Pressure Location X"))
        writer.append(path + '/referencePressureLocation/y',
                      self._ui.referencePressureLocationY.text(), self.tr("Refeerence Pressure Location Y"))
        writer.append(path + '/referencePressureLocation/z',
                      self._ui.referencePressureLocationZ.text(), self.tr("Refeerence Pressure Location Z"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self.OPERATING_CONDITIONS_XPATH

        self._ui.operationPressure.setText(self._db.getValue(path + '/pressure'))
        self._ui.referencePressureLocationX.setText(self._db.getValue(path + '/referencePressureLocation/x'))
        self._ui.referencePressureLocationY.setText(self._db.getValue(path + '/referencePressureLocation/y'))
        self._ui.referencePressureLocationZ.setText(self._db.getValue(path + '/referencePressureLocation/z'))
