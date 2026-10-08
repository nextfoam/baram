#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.boundary.boundary_patch import OpenChannelOutletUpdate
from baramFlow.base.boundary.open_channel_port import OpenChannelOutlet
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .open_channel_outlet_dialog_ui import Ui_OpenChannelOutletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class OpenChannelOutletDialog(ResizableDialog):
    RELATIVE_XPATH = '/openChannelOutlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_OpenChannelOutletDialog()
        self._ui.setupUi(self)

        self._bcid = bcid
        self._xpath = BoundaryDB.getXPath(bcid)

        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, self._ui.dialogContents.layout())

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

            data = OpenChannelOutletUpdate(
                openChannelOutlet=OpenChannelOutlet(
                    meanVelocity=str(PFloat(self._ui.meanVelocity.text(), self.tr("Mean Velocity")))),
                turbulence=self._turbulenceWidget.data())

            BoundaryService.updateBoundaryCondition(self._bcid, data, writer)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.meanVelocity.setText(db.getValue(path + '/meanVelocity'))

        self._turbulenceWidget.load()
