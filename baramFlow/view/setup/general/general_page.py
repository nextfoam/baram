#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.general_db import GeneralDB, SolverType
from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from baramFlow.view.widgets.content_page import ContentPage
from .general_page_ui import Ui_GeneralPage


logger = logging.getLogger(__name__)

GRAVITY_XPATH = GeneralDB.OPERATING_CONDITIONS_XPATH + '/gravity'


class GeneralPage(ContentPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_GeneralPage()
        self._ui.setupUi(self)

        self._load()

        if GeneralDB.getSolverType() == SolverType.DENSITY_BASED:
            self._ui.transient_.setEnabled(False)

    def save(self):
        writer = CoreDBWriter()

        writer.append(GeneralDB.GENERAL_XPATH + '/timeTransient',
                      'true' if self._ui.transient_.isChecked() else 'false', None)
        writer.append(GRAVITY_XPATH + '/direction/x', self._ui.gravityX.text(), self.tr('Gravity X'))
        writer.append(GRAVITY_XPATH + '/direction/y', self._ui.gravityY.text(), self.tr('Gravity Y'))
        writer.append(GRAVITY_XPATH + '/direction/z', self._ui.gravityZ.text(), self.tr('Gravity Z'))
        writer.append(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure',
                      self._ui.operatingPressure.text(), self.tr("Operating Pressure"))

        writer.append(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation/x',
                      self._ui.pressureLocationX.text(), self.tr("Reference Pressure Location X"))
        writer.append(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation/y',
                      self._ui.pressureLocationY.text(), self.tr("Reference Pressure Location Y"))
        writer.append(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation/z',
                      self._ui.pressureLocationZ.text(), self.tr("Reference Pressure Location Z"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
            return False

        return True

    def _load(self):
        db = coredb.CoreDB()

        xpath = GeneralDB.GENERAL_XPATH + '/timeTransient'
        timeTransient = db.getValue(xpath)
        if timeTransient == 'true':
            self._ui.transient_.setChecked(True)
        else:
            self._ui.steady.setChecked(True)

        self._ui.gravityX.setText(db.getValue(GRAVITY_XPATH + '/direction/x'))
        self._ui.gravityY.setText(db.getValue(GRAVITY_XPATH + '/direction/y'))
        self._ui.gravityZ.setText(db.getValue(GRAVITY_XPATH + '/direction/z'))
        self._ui.operatingPressure.setText(db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))

        self._ui.gravity.setDisabled(db.getAttribute(GRAVITY_XPATH, 'disabled') == 'true')

        self._ui.pressureLocationX.setText(
            db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation/x'))
        self._ui.pressureLocationY.setText(
            db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation/y'))
        self._ui.pressureLocationZ.setText(
            db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation/z'))

