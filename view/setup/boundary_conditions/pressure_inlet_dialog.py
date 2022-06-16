#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.widgets.resizable_dialog import ResizableDialog
from view.setup.models.models_db import ModelsDB
from .pressure_inlet_dialog_ui import Ui_PressureInletDialog
from .turbulence_model_helper import TurbulenceModelHelper
from .temperature_widget import TemperatureWidget
from .boundary_db import BoundaryDB


class PressureInletDialog(ResizableDialog):
    RELATIVE_PATH = '/pressureInlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_PressureInletDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)
        self._turbulenceWidget = TurbulenceModelHelper.createWidget(self._xpath)
        self._temperatureWidget = None

        layout = self._ui.dialogContents.layout()
        if self._turbulenceWidget is not None:
            layout.addWidget(self._turbulenceWidget)
        if ModelsDB.isEnergyModelOn():
            self._temperatureWidget = TemperatureWidget(self._xpath)
            layout.addWidget(self._temperatureWidget)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_PATH

        writer = CoreDBWriter()
        writer.append(path + '/pressure', self._ui.totalPressure.text(), self.tr("Total Pressure"))

        if self._turbulenceWidget is not None:
            self._turbulenceWidget.appendToWriter(writer)
        if self._temperatureWidget is not None:
            self._temperatureWidget.appendToWriter(writer)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_PATH

        self._ui.totalPressure.setText(self._db.getValue(path + '/pressure'))

        if self._turbulenceWidget is not None:
            self._turbulenceWidget.load()
        if self._temperatureWidget is not None:
            self._temperatureWidget.load()
