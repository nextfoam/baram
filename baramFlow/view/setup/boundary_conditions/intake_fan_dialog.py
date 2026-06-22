#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import UUID
import qasync

from PySide6.QtCore import Qt

from libbaram.natural_name_uuid import uuidToNnstr
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.base import TrackedData
from baramFlow.base.boundary.boundary_patch import IntakeFanUpdate
from baramFlow.base.file_data_manager import TableDataForFileDB
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.project import Project
from baramFlow.coredb.region_db import RegionDB
from baramFlow.services.boundary.boundary_service import BoundaryService
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
        self._fanCurve = TrackedData()

        self._bcid = bcid
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
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
        else:
            super().keyPressEvent(event)

    @qasync.asyncSlot()
    async def _accept(self):
        #
        # Validation check for parameters
        #
        if self._fanCurve.isNone() and self._fanCurveName.int == 0:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Edit Fan Curve'))
            return

        valid, msg = self._volumeFractionWidget.validate()
        if not valid:
            await AsyncMessageBox().warning(self, self.tr('Warning'), msg)
            return

        # ToDo: Add validation for other parameters

        try:
            writer = CoreDBWriter()

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

            data = IntakeFanUpdate(
                turbulence=self._turbulenceWidget.data(),
                pressure=self._ui.totalPressure.pFloat(self.tr("Total Pressure")),
                fanCurve=TableDataForFileDB(data=self._fanCurve.data()) if self._fanCurve.isModified() else None)

            BoundaryService.updateBoundaryCondition(self._bcid, data, writer)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

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
        if self._fanCurve.isNone() and self._fanCurveName.int != 0:
            df = Project.instance().fileDB().getDataFrame(uuidToNnstr(self._fanCurveName))
            if df is not None:
                self._fanCurve = TrackedData(df.values.tolist())

        self._dialog = PiecewiseLinearDialog(self, self.tr('Fan Curve'), 'Q', 'm3/s', ['P'], 'Pa', self._fanCurve.data())
        self._dialog.accepted.connect(self._fanCurveAccepted)
        self._dialog.open()

    def _fanCurveAccepted(self):
        self._fanCurve.setData(self._dialog.getData())

