#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.boundary_db import BoundaryDB
from view.widgets.resizable_dialog import ResizableDialog
from .farfield_riemann_dialog_ui import Ui_FarfieldRiemannDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class FarfieldRiemannDialog(ResizableDialog):
    RELATIVE_XPATH = '/farFieldRiemann'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FarfieldRiemannDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)

        layout = self._ui.dialogContents.layout()
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._volumeFractionWidget = ConditionalWidgetHelper.volumeFractionWidget(BoundaryDB.getBoundaryRegion(bcid),
                                                                                  self._xpath, layout)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/flowDirection/x', self._ui.xComponent.text(), self.tr("X-Velocity"))
        writer.append(path + '/flowDirection/y', self._ui.yComponent.text(), self.tr("Y-Velocity"))
        writer.append(path + '/flowDirection/z', self._ui.zComponent.text(), self.tr("Z-Velocity"))
        writer.append(path + '/machNumber', self._ui.machNumber.text(), self.tr("Mach Number"))
        writer.append(path + '/staticPressure', self._ui.staticPressure.text(), self.tr("Static Pressure"))
        writer.append(path + '/staticTemperature', self._ui.staticTemperature.text(), self.tr("Static Temperature"))

        if not self._turbulenceWidget.appendToWriter(writer):
            return

        if not self._volumeFractionWidget.appendToWriter(writer):
            return

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.xComponent.setText(self._db.getValue(path + '/flowDirection/x'))
        self._ui.yComponent.setText(self._db.getValue(path + '/flowDirection/y'))
        self._ui.zComponent.setText(self._db.getValue(path + '/flowDirection/z'))
        self._ui.machNumber.setText(self._db.getValue(path + '/machNumber'))
        self._ui.staticPressure.setText(self._db.getValue(path + '/staticPressure'))
        self._ui.staticTemperature.setText(self._db.getValue(path + '/staticTemperature'))

        self._turbulenceWidget.load()
        self._volumeFractionWidget.load()
