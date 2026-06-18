#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.boundary.boundary_patch import SupersonicInflowUpdate
from baramFlow.base.boundary.supersonic_inflow import SupersonicInflow
from baramFlow.base.xml_helper import Vector
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .supersonic_inflow_dialog_ui import Ui_SupersonicInflowDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class SupersonicInflowDialog(ResizableDialog):
    RELATIVE_XPATH = '/supersonicInflow'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_SupersonicInflowDialog()
        self._ui.setupUi(self)

        self._bcid = bcid
        self._xpath = BoundaryDB.getXPath(bcid)

        layout = self._ui.dialogContents.layout()

        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            writer = CoreDBWriter()
            if not self._turbulenceWidget.appendToWriter(writer):
                return

            data = SupersonicInflowUpdate(
                supersonicInflow=SupersonicInflow(
                    velocity=Vector(x=PFloat(self._ui.xVelocity.text(), self.tr("X-Velocity")),
                                    y=PFloat(self._ui.yVelocity.text(), self.tr("Y-Velocity")),
                                    z=PFloat(self._ui.zVelocity.text(), self.tr("Z-Velocity"))),
                    staticPressure=PFloat(self._ui.staticPressure.text(), self.tr("Static Pressure")),
                    staticTemperature=PFloat(self._ui.staticTemperature.text(), self.tr("Static Temperature"))),
                turbulence=self._turbulenceWidget.data())

            BoundaryService.updateBoundaryCondition(self._bcid, data, writer)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._ui.xVelocity.setText(db.getValue(xpath + '/velocity/x'))
        self._ui.yVelocity.setText(db.getValue(xpath + '/velocity/y'))
        self._ui.zVelocity.setText(db.getValue(xpath + '/velocity/z'))
        self._ui.staticPressure.setText(db.getValue(xpath + '/staticPressure'))
        self._ui.staticTemperature.setText(db.getValue(xpath + '/staticTemperature'))

        self._turbulenceWidget.load()
