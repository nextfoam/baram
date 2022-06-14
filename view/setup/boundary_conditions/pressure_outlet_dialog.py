#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.widgets.resizable_dialog import ResizableDialog
from view.setup.models.models_db import ModelsDB
from .pressure_outlet_dialog_ui import Ui_PressureOutletDialog
from .turbulence_model_helper import TurbulenceModelHelper
from .boundary_db import BoundaryDB


class PressureOutletDialog(ResizableDialog):
    RELATIVE_PATH = '/pressureOutlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_PressureOutletDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getBoundaryXPath(bcid)
        self._turbulenceWidget = TurbulenceModelHelper.createWidget(self._xpath)

        if self._turbulenceWidget is not None:
            self._ui.calculateBackflow.layout().insertWidget(0, self._turbulenceWidget)

        if not ModelsDB.isEnergyModelOn():
            self._ui.backflowTotalTemperatureWidget.hide()

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_PATH

        writer = CoreDBWriter()
        writer.append(path + '/totalPressure', self._ui.totalPressure.text(), self.tr("Total Pressure"))
        if self._ui.calculateBackflow.isChecked():
            writer.append(path + '/calculatedBackflow', "true", None)

            if self._turbulenceWidget is not None:
                self._turbulenceWidget.appendToWriter(writer)

            writer.append(path + '/backflowTotalTemperature',
                          self._ui.backflowTotalTemperature.text(), self.tr("Backflow Total Temperature"))
        else:
            writer.append(path + '/calculatedBackflow', "false", None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_PATH

        self._ui.totalPressure.setText(self._db.getValue(path + '/totalPressure'))
        self._ui.calculateBackflow.setChecked(self._db.getValue(path + '/calculatedBackflow') == "true")
        if self._turbulenceWidget is not None:
            self._turbulenceWidget.load()
        if ModelsDB.isEnergyModelOn():
            self._ui.backflowTotalTemperature.setText(self._db.getValue(path + '/backflowTotalTemperature'))
