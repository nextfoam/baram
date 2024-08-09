#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .subsonic_inlet_dialog_ui import Ui_SubsonicInletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class SubsonicInletDialog(ResizableDialog):
    RELATIVE_XPATH = '/subsonicInlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_SubsonicInletDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)

        layout = self._ui.dialogContents.layout()

        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/flowDirection/x', self._ui.xComponent.text(), self.tr("X-Component"))
        writer.append(path + '/flowDirection/y', self._ui.yComponent.text(), self.tr("Y-Component"))
        writer.append(path + '/flowDirection/z', self._ui.zComponent.text(), self.tr("Z-Component"))
        writer.append(path + '/totalPressure', self._ui.totalPressure.text(), self.tr("Pressure"))
        writer.append(path + '/totalTemperature', self._ui.totalTemperature.text(), self.tr("Pressure"))

        if not self._turbulenceWidget.appendToWriter(writer):
            return

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.xComponent.setText(db.getValue(path + '/flowDirection/x'))
        self._ui.yComponent.setText(db.getValue(path + '/flowDirection/y'))
        self._ui.zComponent.setText(db.getValue(path + '/flowDirection/z'))
        self._ui.totalPressure.setText(db.getValue(path + '/totalPressure'))
        self._ui.totalTemperature.setText(db.getValue(path + '/totalTemperature'))

        self._turbulenceWidget.load()
