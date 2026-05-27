#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.base import Vector
from baramFlow.base.boundary.boundary_patch import SubsonicInletPatch
from baramFlow.base.boundary.subsonic_inle import SubsonicInlet
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .subsonic_inlet_dialog_ui import Ui_SubsonicInletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class SubsonicInletDialog(ResizableDialog):
    RELATIVE_XPATH = '/subsonicInlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_SubsonicInletDialog()
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

            data = SubsonicInletPatch(
                subsonicInlet=SubsonicInlet(
                    flowDirection=Vector(x=PFloat(self._ui.xComponent.text(), self.tr('X-Component')),
                                         y=PFloat(self._ui.yComponent.text(), self.tr('Y-Component')),
                                         z=PFloat(self._ui.zComponent.text(), self.tr('Z-Component'))),
                    totalPressure=str(PFloat(self._ui.totalPressure.text(), self.tr("Pressure"))),
                    totalTemperature=str(PFloat(self._ui.totalTemperature.text(), self.tr("Pressure")))),
                turbulence=self._turbulenceWidget.data())

            BoundaryService.updateBoundaryCondition(self._bcid, data, writer)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.xComponent.setText(db.getValue(path + '/flowDirection/x'))
        self._ui.yComponent.setText(db.getValue(path + '/flowDirection/y'))
        self._ui.zComponent.setText(db.getValue(path + '/flowDirection/z'))
        self._ui.totalPressure.setText(db.getValue(path + '/totalPressure'))
        self._ui.totalTemperature.setText(db.getValue(path + '/totalTemperature'))

        self._turbulenceWidget.load()
