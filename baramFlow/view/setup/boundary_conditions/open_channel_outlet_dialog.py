#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .open_channel_outlet_dialog_ui import Ui_OpenChannelOutletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class OpenChannelOutletDialog(ResizableDialog):
    RELATIVE_XPATH = '/openChannelOutlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_OpenChannelOutletDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, self._ui.dialogContents.layout())

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/meanVelocity', self._ui.meanVelocity.text(), self.tr("Mean Velocity"))

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

        self._ui.meanVelocity.setText(db.getValue(path + '/meanVelocity'))

        self._turbulenceWidget.load()
