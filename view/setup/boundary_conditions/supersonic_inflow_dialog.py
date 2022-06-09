#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter

from PySide6.QtWidgets import QMessageBox

from view.widgets.resizable_dialog import ResizableDialog
from .supersonic_inflow_dialog_ui import Ui_SupersonicInflowDialog
from .turbulence_model import TurbulenceModel
from .boundary_db import BoundaryDB


class SupersonicInflowDialog(ResizableDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_SupersonicInflowDialog()
        self._ui.setupUi(self)

        self._xpath = f'{BoundaryDB.BOUNDARY_CONDITIONS_XPATH}/boundaryCondition[@bcid="{bcid}"]'
        self._boundaryCondition = None

        self._db = coredb.CoreDB()

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)

        self._load()

    def _load(self):
        path = self._xpath + '/supersonicInflow'

        self._ui.xVelocity.setText(self._db.getValue(path + '/velocity/x'))
        self._ui.yVelocity.setText(self._db.getValue(path + '/velocity/y'))
        self._ui.zVelocity.setText(self._db.getValue(path + '/velocity/z'))
        self._ui.staticPressure.setText(self._db.getValue(path + '/staticPressure'))
        self._ui.staticTemperature.setText(self._db.getValue(path + '/staticTemperature'))

        self._turbulenceWidget.load(self._db, self._xpath)

    def accept(self):
        path = self._xpath + '/supersonicInflow'

        writer = CoreDBWriter()
        writer.append(path + '/velocity/x', self._ui.xVelocity.text(), self.tr("X-Velocity"))
        writer.append(path + '/velocity/y', self._ui.yVelocity.text(), self.tr("Y-Velocity"))
        writer.append(path + '/velocity/z', self._ui.zVelocity.text(), self.tr("Z-Velocity"))
        writer.append(path + '/staticPressure', self._ui.staticPressure.text(), self.tr("Static Pressure"))
        writer.append(path + '/staticTemperature', self._ui.staticTemperature.text(), self.tr("Static Temperature"))

        self._turbulenceWidget.appendToWriter(writer, self._xpath)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.close()
