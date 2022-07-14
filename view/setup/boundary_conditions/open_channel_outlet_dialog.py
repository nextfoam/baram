#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.boundary_db import BoundaryDB
from view.widgets.resizable_dialog import ResizableDialog
from .open_channel_outlet_dialog_ui import Ui_OpenChannelOutletDialog
from .turbulence_model_helper import TurbulenceModelHelper


class OpenChannelOutletDialog(ResizableDialog):
    RELATIVE_XPATH = '/openChannelOutlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_OpenChannelOutletDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)
        self._turbulenceWidget = TurbulenceModelHelper.createWidget(self._xpath)

        if self._turbulenceWidget is not None:
            self._ui.dialogContents.layout().addWidget(self._turbulenceWidget)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/meanVelocity', self._ui.meanVelocity.text(), self.tr("Mean Velocity"))

        if self._turbulenceWidget is not None:
            self._turbulenceWidget.appendToWriter(writer)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.meanVelocity.setText(self._db.getValue(path + '/meanVelocity'))

        if self._turbulenceWidget is not None:
            self._turbulenceWidget.load()
