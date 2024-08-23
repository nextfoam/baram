#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync
from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .free_stream_dialog_ui import Ui_FreeStreamDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class FreeStreamDialog(ResizableDialog):
    RELATIVE_XPATH = '/freeStream'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FreeStreamDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)

        self._turbulenceWidget = None
        self._temperatureWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        layout = self._ui.dialogContents.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._temperatureWidget = ConditionalWidgetHelper.temperatureWidget(self._xpath, bcid, layout)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(RegionDB.getMaterial(rname), layout)

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
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

        if not self._scalarsWidget.appendToWriter(writer, self._xpath + '/userDefinedScalars'):
            return

        if not await self._speciesWidget.appendToWriter(writer, self._xpath + '/species'):
            return

        errorCount = writer.write()
        if errorCount > 0:
            self._temperatureWidget.rollbackWriting()
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self._temperatureWidget.completeWriting()
            self.accept()

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.xVelocity.setText(db.getValue(path + '/streamVelocity/x'))
        self._ui.yVelocity.setText(db.getValue(path + '/streamVelocity/y'))
        self._ui.zVelocity.setText(db.getValue(path + '/streamVelocity/z'))
        self._ui.pressure.setText(db.getValue(path + '/pressure'))

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._temperatureWidget.freezeProfileToConstant()
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
