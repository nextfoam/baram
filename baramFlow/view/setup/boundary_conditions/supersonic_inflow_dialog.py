#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .supersonic_inflow_dialog_ui import Ui_SupersonicInflowDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class SupersonicInflowDialog(ResizableDialog):
    RELATIVE_XPATH = '/supersonicInflow'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_SupersonicInflowDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)

        layout = self._ui.dialogContents.layout()

        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)

        self._load()

    def accept(self):
        xpath = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(xpath + '/velocity/x', self._ui.xVelocity.text(), self.tr("X-Velocity"))
        writer.append(xpath + '/velocity/y', self._ui.yVelocity.text(), self.tr("Y-Velocity"))
        writer.append(xpath + '/velocity/z', self._ui.zVelocity.text(), self.tr("Z-Velocity"))
        writer.append(xpath + '/staticPressure', self._ui.staticPressure.text(), self.tr("Static Pressure"))
        writer.append(xpath + '/staticTemperature', self._ui.staticTemperature.text(), self.tr("Static Temperature"))

        if not self._turbulenceWidget.appendToWriter(writer):
            return

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._ui.xVelocity.setText(db.getValue(xpath + '/velocity/x'))
        self._ui.yVelocity.setText(db.getValue(xpath + '/velocity/y'))
        self._ui.zVelocity.setText(db.getValue(xpath + '/velocity/z'))
        self._ui.staticPressure.setText(db.getValue(xpath + '/staticPressure'))
        self._ui.staticTemperature.setText(db.getValue(xpath + '/staticTemperature'))

        self._turbulenceWidget.load()
