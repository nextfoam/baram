#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.models_db import ModelsDB
from coredb.boundary_db import BoundaryDB
from view.widgets.resizable_dialog import ResizableDialog
from .pressure_outlet_dialog_ui import Ui_PressureOutletDialog
from .turbulence_model_helper import TurbulenceModelHelper
from .volume_franction_widget import VolumeFractionWidget


class PressureOutletDialog(ResizableDialog):
    RELATIVE_XPATH = '/pressureOutlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_PressureOutletDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)
        self._turbulenceWidget = TurbulenceModelHelper.createWidget(self._xpath)

        if self._turbulenceWidget:
            self._ui.calculateBackflow.layout().insertWidget(0, self._turbulenceWidget)
            if not ModelsDB.isEnergyModelOn():
                self._ui.backflowTotalTemperatureWidget.hide()
        elif not ModelsDB.isEnergyModelOn():
            self._ui.calculateBackflow.hide()

        layout = self._ui.dialogContents.layout()
        self._volumeFractionWidget = VolumeFractionWidget(bcid)
        if self._volumeFractionWidget.on():
            layout.addWidget(self._volumeFractionWidget)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/totalPressure', self._ui.totalPressure.text(), self.tr("Total Pressure"))
        if self._ui.calculateBackflow.isChecked():
            writer.append(path + '/calculatedBackflow', "true", None)

            if self._turbulenceWidget:
                self._turbulenceWidget.appendToWriter(writer)

            if self._ui.backflowTotalTemperatureWidget.isVisible():
                writer.append(path + '/backflowTotalTemperature',
                              self._ui.backflowTotalTemperature.text(), self.tr("Backflow Total Temperature"))
        else:
            writer.append(path + '/calculatedBackflow', "false", None)

        if not self._volumeFractionWidget.appendToWriter(writer):
            return

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.totalPressure.setText(self._db.getValue(path + '/totalPressure'))
        self._ui.calculateBackflow.setChecked(self._db.getValue(path + '/calculatedBackflow') == "true")
        if self._turbulenceWidget:
            self._turbulenceWidget.load()
        if ModelsDB.isEnergyModelOn():
            self._ui.backflowTotalTemperature.setText(self._db.getValue(path + '/backflowTotalTemperature'))

        self._volumeFractionWidget.load()
