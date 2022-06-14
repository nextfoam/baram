#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter

from PySide6.QtWidgets import QMessageBox

from view.widgets.resizable_dialog import ResizableDialog
from .supersonic_inflow_dialog_ui import Ui_SupersonicInflowDialog
from .turbulence_model_helper import TurbulenceModelHelper
from .boundary_db import BoundaryDB


class SupersonicInflowDialog(ResizableDialog):
    RELATIVE_PATH = '/supersonicInflow'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_SupersonicInflowDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getBoundaryXPath(bcid)
        self._turbulenceWidget = TurbulenceModelHelper.createWidget(self._xpath)

        if self._turbulenceWidget is not None:
            self._ui.dialogContents.layout().addWidget(self._turbulenceWidget)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_PATH

        writer = CoreDBWriter()
        writer.append(path + '/velocity/x', self._ui.xVelocity.text(), self.tr("X-Velocity"))
        writer.append(path + '/velocity/y', self._ui.yVelocity.text(), self.tr("Y-Velocity"))
        writer.append(path + '/velocity/z', self._ui.zVelocity.text(), self.tr("Z-Velocity"))
        writer.append(path + '/staticPressure', self._ui.staticPressure.text(), self.tr("Static Pressure"))
        writer.append(path + '/staticTemperature', self._ui.staticTemperature.text(), self.tr("Static Temperature"))

        if self._turbulenceWidget is not None:
            self._turbulenceWidget.appendToWriter(writer)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_PATH

        self._ui.xVelocity.setText(self._db.getValue(path + '/velocity/x'))
        self._ui.yVelocity.setText(self._db.getValue(path + '/velocity/y'))
        self._ui.zVelocity.setText(self._db.getValue(path + '/velocity/z'))
        self._ui.staticPressure.setText(self._db.getValue(path + '/staticPressure'))
        self._ui.staticTemperature.setText(self._db.getValue(path + '/staticTemperature'))

        if self._turbulenceWidget is not None:
            self._turbulenceWidget.load()
