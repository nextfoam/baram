#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from uuid import UUID

from PySide6.QtCore import Qt

from baramFlow.base.file_data_manager import TableDataForFileDB
from libbaram.natural_name_uuid import uuidToNnstr
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.base import TrackedData
from baramFlow.base.boundary.boundary_patch import FanUpdate
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.base.boundary.fan import Fan
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.project import Project
from baramFlow.view.widgets.piecewise_linear_dialog import PiecewiseLinearDialog
from .fan_dialog_ui import Ui_FanDialog
from .coupled_boundary_condition_dialog import CoupledBoundaryConditionDialog


class FanDialog(CoupledBoundaryConditionDialog):
    BOUNDARY_TYPE = BoundaryType.FAN
    RELATIVE_XPATH = '/fan'

    def __init__(self, parent, bcid):
        super().__init__(parent, bcid)
        self._ui = Ui_FanDialog()
        self._ui.setupUi(self)

        self._coupleNameDisplay = self._ui.coupledBoundary

        self._xpath = BoundaryDB.getXPath(bcid)

        self._fanCurveName: UUID
        self._fanCurve = TrackedData()

        self._coupleNameDisplay = self._ui.coupledBoundary
        self._dialog = None

        self._connectSignalsSlots()
        self._load()

    def closeEvent(self, event):
        self._ui.cancel.click()
        event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._ui.cancel.click()
            event.ignore()
        else:
            super().keyPressEvent(event)

    def _connectSignalsSlots(self):
        self._ui.editFanCurve.clicked.connect(self._editFanCurve)
        self._ui.coupledBoundarySelect.clicked.connect(self._openCoupledBoundarySelector)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self._reject)

    def _load(self):
        db = coredb.CoreDB()

        self._setCoupledBoundary(db.getValue(self._xpath + '/coupledBoundary'))
        self._fanCurveName = UUID(db.getValue(self._xpath + '/fanCurveName'))
        self._ui.reverseFanDirection.setChecked(db.getBool(self._xpath + '/fan/reverseDirection'))

    @qasync.asyncSlot()
    async def _accept(self):
        if self._coupledBoundary == '0':
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Coupled Boundary'))
            return

        if self._fanCurve.isNone() and self._fanCurveName.int == 0:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Edit Fan Curve'))
            return

        data = FanUpdate(
            fan=Fan(reverseDirection=self._ui.reverseFanDirection.isChecked(),
                    fanCurve=TableDataForFileDB(data=self._fanCurve.data()) if self._fanCurve.isModified() else None),
            coupledBoundary=self._coupledBoundary)

        try:
            BoundaryService.updateBoundaryCondition(self._bcid, data)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))

        super().accept()

    @qasync.asyncSlot()
    async def _reject(self):
        if self._fanCurveName.int == 0:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Be sure to edit Fan Curve'))
        else:
            self.reject()

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

    def _setCoupledBoundary(self, bcid):
        super()._setCoupledBoundary(bcid)

        if self._coupledBoundary == '0':
            self._ui.zoneAverageDirectionX.clear()
            self._ui.zoneAverageDirectionY.clear()
            self._ui.zoneAverageDirectionZ.clear()
        else:
            zoneAverageDirection = BoundaryService.getZoneAverageDirectionForFan(self._bcid, self._coupledBoundary)
            self._ui.zoneAverageDirectionX.setText(str(zoneAverageDirection[0]))
            self._ui.zoneAverageDirectionY.setText(str(zoneAverageDirection[1]))
            self._ui.zoneAverageDirectionZ.setText(str(zoneAverageDirection[2]))

    def _writeConditions(self, db, xpath):
        db.setValue(xpath + '/fanCurveName', str(self._fanCurveName), self.tr("Fan Curve Name"))
