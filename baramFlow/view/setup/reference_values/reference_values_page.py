#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QMessageBox

from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.project import Project
from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from baramFlow.view.widgets.content_page import ContentPage
from .reference_values_page_ui import Ui_ReferenceValuesPage


class ReferenceValuesPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ReferenceValuesPage()
        self._ui.setupUi(self)

        self._connectSignalsSlots()
        self._updateEnabled()
        self._load()

    @qasync.asyncSlot()
    async def save(self):
        xpath = ReferenceValuesDB.REFERENCE_VALUES_XPATH

        writer = CoreDBWriter()
        writer.append(xpath + '/area', self._ui.area.text(), self.tr("Area"))
        writer.append(xpath + '/density', self._ui.density.text(), self.tr("Density"))
        writer.append(xpath + '/length', self._ui.length.text(), self.tr("Length"))
        writer.append(xpath + '/velocity', self._ui.velocity.text(), self.tr("Velocity"))
        writer.append(xpath + '/pressure', self._ui.pressure.text(), self.tr("Pressure"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
            return False

        return True

    def _connectSignalsSlots(self):
        Project.instance().solverStatusChanged.connect(self._updateEnabled)

    def _load(self):
        db = coredb.CoreDB()

        xpath = ReferenceValuesDB.REFERENCE_VALUES_XPATH
        self._ui.area.setText(db.getValue(xpath + '/area'))
        self._ui.density.setText(db.getValue(xpath + '/density'))
        self._ui.length.setText(db.getValue(xpath + '/length'))
        self._ui.velocity.setText(db.getValue(xpath + '/velocity'))
        self._ui.pressure.setText(db.getValue(xpath + '/pressure'))

    def _updateEnabled(self):
        self.setEnabled(not CaseManager().isActive())
