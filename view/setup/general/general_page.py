#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.general_db import GeneralDB, SolverType
from view.widgets.content_page import ContentPage
from .general_page_ui import Ui_GeneralPage


logger = logging.getLogger(__name__)

GRAVITY_XPATH = GeneralDB.OPERATING_CONDITIONS_XPATH + '/gravity/direction'


class GeneralPage(ContentPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_GeneralPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._load()

        if GeneralDB.getSolverType() == SolverType.DENSITY_BASED:
            self._ui.transient_.setEnabled(False)

    def hideEvent(self, ev):
        if not ev.spontaneous():
            self.save()

        return super().hideEvent(ev)

    def save(self):
        writer = CoreDBWriter()

        writer.append(GeneralDB.GENERAL_XPATH + '/timeTransient',
                      'true' if self._ui.transient_.isChecked() else 'false', None)
        writer.append(GRAVITY_XPATH + '/x', self._ui.gravityX.text(), self.tr('Gravity X'))
        writer.append(GRAVITY_XPATH + '/y', self._ui.gravityY.text(), self.tr('Gravity Y'))
        writer.append(GRAVITY_XPATH + '/z', self._ui.gravityZ.text(), self.tr('Gravity Z'))
        writer.append(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure',
                      self._ui.operatingPressure.text(), self.tr("Operating Pressure"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
            return False

        return True

    def _load(self):
        xpath = GeneralDB.GENERAL_XPATH + '/timeTransient'
        timeTransient = self._db.getValue(xpath)
        if timeTransient == 'true':
            self._ui.transient_.setChecked(True)
        else:
            self._ui.steady.setChecked(True)

        self._ui.gravityX.setText(self._db.getValue(GRAVITY_XPATH + '/x'))
        self._ui.gravityY.setText(self._db.getValue(GRAVITY_XPATH + '/y'))
        self._ui.gravityZ.setText(self._db.getValue(GRAVITY_XPATH + '/z'))
        self._ui.operatingPressure.setText(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))

