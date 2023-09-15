#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baram.coredb import coredb
from baram.coredb.coredb_writer import CoreDBWriter
from baram.coredb.reference_values_db import ReferenceValuesDB
from baram.view.widgets.content_page import ContentPage
from .reference_values_page_ui import Ui_ReferenceValuesPage


class ReferenceValuesPage(ContentPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ReferenceValuesPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._load()

    def save(self):
        writer = CoreDBWriter()
        xpath = ReferenceValuesDB.REFERENCE_VALUES_XPATH

        writer.append(xpath + '/area', self._ui.area.text(), self.tr("Area"))
        writer.append(xpath + '/density', self._ui.density.text(), self.tr("Density"))
        writer.append(xpath + '/length', self._ui.length.text(), self.tr("Length"))
        writer.append(xpath + '/velocity', self._ui.velocity.text(), self.tr("Velocity"))
        writer.append(xpath + '/pressure', self._ui.pressure.text(), self.tr("Pressure"))

        writer.append(xpath + '/referencePressureLocation/x',
                      self._ui.pressureLocationX.text(), self.tr("Reference Pressure Location X"))
        writer.append(xpath + '/referencePressureLocation/y',
                      self._ui.pressureLocationY.text(), self.tr("Reference Pressure Location Y"))
        writer.append(xpath + '/referencePressureLocation/z',
                      self._ui.pressureLocationZ.text(), self.tr("Reference Pressure Location Z"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
            return False

        return True

    def _load(self):
        xpath = ReferenceValuesDB.REFERENCE_VALUES_XPATH
        self._ui.area.setText(self._db.getValue(xpath + '/area'))
        self._ui.density.setText(self._db.getValue(xpath + '/density'))
        self._ui.length.setText(self._db.getValue(xpath + '/length'))
        self._ui.velocity.setText(self._db.getValue(xpath + '/velocity'))
        self._ui.pressure.setText(self._db.getValue(xpath + '/pressure'))

        self._ui.pressureLocationX.setText(self._db.getValue(xpath + '/referencePressureLocation/x'))
        self._ui.pressureLocationY.setText(self._db.getValue(xpath + '/referencePressureLocation/y'))
        self._ui.pressureLocationZ.setText(self._db.getValue(xpath + '/referencePressureLocation/z'))
