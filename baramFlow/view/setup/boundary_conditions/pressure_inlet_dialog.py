#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .pressure_inlet_dialog_ui import Ui_PressureInletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class PressureInletDialog(ResizableDialog):
    RELATIVE_XPATH = '/pressureInlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_PressureInletDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)

        self._turbulenceWidget = None
        self._temperatureWidget = None
        self._volumeFractionWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        layout = self._ui.dialogContents.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._temperatureWidget = ConditionalWidgetHelper.temperatureWidget(self._xpath, bcid, layout)
        self._volumeFractionWidget = ConditionalWidgetHelper.volumeFractionWidget(rname, layout)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(RegionDB.getMaterial(rname), layout)

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        #
        # Validation check for parameters
        #
        valid, msg = self._volumeFractionWidget.validate()
        if not valid:
            await AsyncMessageBox().warning(self, self.tr('Warning'), msg)
            return
        # ToDo: Add validation for other parameters

        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/pressure', self._ui.totalPressure.text(), self.tr("Total Pressure"))

        if not self._turbulenceWidget.appendToWriter(writer):
            return

        if not self._temperatureWidget.appendToWriter(writer):
            return

        if not await self._volumeFractionWidget.appendToWriter(writer, self._xpath + '/volumeFractions'):
            return

        if not self._scalarsWidget.appendToWriter(writer, self._xpath + '/userDefinedScalars'):
            return

        if not await self._speciesWidget.appendToWriter(writer, self._xpath + '/species'):
            return

        errorCount = writer.write()
        if errorCount > 0:
            self._temperatureWidget.rollbackWriting()
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self._temperatureWidget.completeWriting()
            self.accept()

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.totalPressure.setText(db.getValue(path + '/pressure'))

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._temperatureWidget.freezeProfileToConstant()
        self._volumeFractionWidget.load(self._xpath + '/volumeFractions')
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
