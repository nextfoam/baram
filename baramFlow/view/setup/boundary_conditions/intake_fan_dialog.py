#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import UUID, uuid4
import qasync

import pandas as pd
from PySide6.QtCore import Qt

from libbaram.natural_name_uuid import uuidToNnstr
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.project import Project
from baramFlow.coredb.region_db import RegionDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from baramFlow.view.widgets.piecewise_linear_dialog import PiecewiseLinearDialog
from .conditional_widget_helper import ConditionalWidgetHelper
from .intake_fan_dialog_ui import Ui_IntakeFanDialog


class IntakeFanDialog(ResizableDialog):
    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_IntakeFanDialog()
        self._ui.setupUi(self)

        self._dialog: PiecewiseLinearDialog
        self._fanCurveName: UUID
        self._fanCurve: list[list[float]] = []

        self._xpath = BoundaryDB.getXPath(bcid)

        layout = self._ui.dialogContents.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._temperatureWidget = ConditionalWidgetHelper.temperatureWidget(self._xpath, bcid, layout)
        self._volumeFractionWidget = ConditionalWidgetHelper.volumeFractionWidget(rname, layout)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(RegionDB.getMaterial(rname), layout)

        self._connectSignalsSlots()

        self._load()

    def closeEvent(self, event):
        self._ui.cancel.click()
        event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            event.ignore()
        else:
            super().keyPressEvent(event)

    @qasync.asyncSlot()
    async def _accept(self):
        #
        # Validation check for parameters
        #
        df = pd.DataFrame(self._fanCurve)
        if df.empty:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Edit Fan Curve'))
            return

        valid, msg = self._volumeFractionWidget.validate()
        if not valid:
            await AsyncMessageBox().warning(self, self.tr('Warning'), msg)
            return

        if len(self._fanCurve[0]) == 0:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Fan Curve is not configured.'))
            return

        # ToDo: Add validation for other parameters

        writer = CoreDBWriter()
        writer.append(self._xpath + '/pressure', self._ui.totalPressure.text(), self.tr("Total Pressure"))

        if self._fanCurveName.int == 0:
            self._fanCurveName = uuid4()
            writer.append(self._xpath + '/fanCurveName', str(self._fanCurveName), self.tr("Fan Curve Name"))

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
            df = pd.DataFrame(self._fanCurve)
            Project.instance().fileDB().putDataFrame(uuidToNnstr(self._fanCurveName), df)

            self._temperatureWidget.completeWriting()
            super().accept()

    @qasync.asyncSlot()
    async def _reject(self):
        if self._fanCurveName.int == 0:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Be sure to edit Fan Curve'))
        else:
            self.reject()

    def _load(self):
        db = coredb.CoreDB()
        self._ui.totalPressure.setText(db.getValue(self._xpath + '/pressure'))

        self._fanCurveName = UUID(db.getValue(self._xpath + '/fanCurveName'))
        if self._fanCurveName.int != 0:
            df = Project.instance().fileDB().getDataFrame(uuidToNnstr(self._fanCurveName))
            if df is not None:
                self._fanCurve = df.values.tolist()

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._temperatureWidget.freezeProfileToConstant()
        self._volumeFractionWidget.load(self._xpath + '/volumeFractions')
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

    def _connectSignalsSlots(self):
        self._ui.editFanCurve.clicked.connect(self._editFanCurve)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self._reject)

    def _editFanCurve(self):
        self._dialog = PiecewiseLinearDialog(self, self.tr('Fan Curve'), 'Q', 'm3/s', ['P'], 'Pa', self._fanCurve)
        self._dialog.accepted.connect(self._fanCurveAccepted)
        self._dialog.open()

    def _fanCurveAccepted(self):
        self._fanCurve = self._dialog.getData()

