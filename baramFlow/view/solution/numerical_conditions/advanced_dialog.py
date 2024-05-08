#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.numerical_db import NumericalDB
from .advanced_dialog_ui import Ui_AdvancedDialog


class AdvancedDialog(QDialog):
    RELATIVE_XPATH = '/advanced'

    def __init__(self):
        super().__init__()
        self._ui = Ui_AdvancedDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = NumericalDB.NUMERICAL_CONDITIONS_XPATH + self.RELATIVE_XPATH

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        writer = CoreDBWriter()
        writer.append(self._xpath + '/limits/minimumStaticTemperature', self._ui.minimumStaticTemperature.text(),
                      self.tr("Minimum Static Temperature"))
        writer.append(self._xpath + '/limits/maximumStaticTemperature', self._ui.maximumStaticTemperature.text(),
                      self.tr("Maximum Static Temperature"))
        writer.append(self._xpath + '/limits/maximumViscosityRatio', self._ui.maximumViscosityRatio.text(),
                      self.tr("Maximum Viscosity Ratio"))

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.accept()

    def _load(self):
        self._ui.minimumStaticTemperature.setText(self._db.getValue(self._xpath + '/limits/minimumStaticTemperature'))
        self._ui.maximumStaticTemperature.setText(self._db.getValue(self._xpath + '/limits/maximumStaticTemperature'))
        self._ui.maximumViscosityRatio.setText(self._db.getValue(self._xpath + '/limits/maximumViscosityRatio'))
