#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.reference_values_db import ReferenceValuesDB
from .reference_values_page_ui import Ui_ReferenceValuesPage


class ReferenceValuesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ReferenceValuesPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._load()

    def hideEvent(self, ev):
        if not ev.spontaneous():
            self.save()

        return super().hideEvent(ev)

    def save(self):
        writer = CoreDBWriter()
        xpath = ReferenceValuesDB.REFERENCE_VALUES_XPATH

        writer.append(xpath + '/referencePressureLocation/x',
                      self._ui.referencePressureLocationX.text(), self.tr("Reference Pressure Location X"))
        writer.append(xpath + '/referencePressureLocation/y',
                      self._ui.referencePressureLocationY.text(), self.tr("Reference Pressure Location Y"))
        writer.append(xpath + '/referencePressureLocation/z',
                      self._ui.referencePressureLocationZ.text(), self.tr("Reference Pressure Location Z"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())

    def _load(self):
        xpath = ReferenceValuesDB.REFERENCE_VALUES_XPATH
        self._ui.referencePressureLocationX.setText(self._db.getValue(xpath + '/referencePressureLocation/x'))
        self._ui.referencePressureLocationY.setText(self._db.getValue(xpath + '/referencePressureLocation/y'))
        self._ui.referencePressureLocationZ.setText(self._db.getValue(xpath + '/referencePressureLocation/z'))
