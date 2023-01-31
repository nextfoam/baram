#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.boundary_db import BoundaryDB
from view.widgets.resizable_dialog import ResizableDialog
from .free_stream_dialog_ui import Ui_FreeStreamDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class FreeStreamDialog(ResizableDialog):
    RELATIVE_XPATH = '/freeStream'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FreeStreamDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)

        layout = self._ui.dialogContents.layout()
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._temperatureWidget = ConditionalWidgetHelper.temperatureWidget(self._xpath, bcid, layout)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/streamVelocity/x', self._ui.xVelocity.text(), self.tr("X-Velocity"))
        writer.append(path + '/streamVelocity/y', self._ui.yVelocity.text(), self.tr("Y-Velocity"))
        writer.append(path + '/streamVelocity/z', self._ui.zVelocity.text(), self.tr("Z-Velocity"))
        writer.append(path + '/pressure', self._ui.pressure.text(), self.tr("Pressure"))

        if not self._turbulenceWidget.appendToWriter(writer):
            return

        if not self._temperatureWidget.appendToWriter(writer):
            return

        errorCount = writer.write()
        if errorCount > 0:
            self._temperatureWidget.rollbackWriting()
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self._temperatureWidget.completeWriting()
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.xVelocity.setText(self._db.getValue(path + '/streamVelocity/x'))
        self._ui.yVelocity.setText(self._db.getValue(path + '/streamVelocity/y'))
        self._ui.zVelocity.setText(self._db.getValue(path + '/streamVelocity/z'))
        self._ui.pressure.setText(self._db.getValue(path + '/pressure'))

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._temperatureWidget.freezeProfileToConstant()
