#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from uuid import UUID, uuid4

import pandas as pd
from PySide6.QtCore import Qt

from libbaram.natural_name_uuid import uuidToNnstr
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
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

        self._xpath = BoundaryDB.getXPath(bcid)
        self._coupledBoundary = None

        self._fanCurveName: UUID
        self._fanCurve: list[list[float]] = []

        self._boundarySelector = None
        self._dialog = None

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

    def _connectSignalsSlots(self):
        self._ui.editFanCurve.clicked.connect(self._editFanCurve)
        self._ui.coupledBoundarySelect.clicked.connect(self._selectCoupledBoundary)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self._reject)

    def _load(self):
        db = coredb.CoreDB()

        self._setCoupledBoundary(db.getValue(self._xpath + '/coupledBoundary'))
        self._fanCurveName = UUID(db.getValue(self._xpath + '/fanCurveName'))

        if self._fanCurveName.int != 0:
            df = Project.instance().fileDB().getDataFrame(uuidToNnstr(self._fanCurveName))
            if df is not None:
                self._fanCurve = df.values.tolist()

    @qasync.asyncSlot()
    async def _accept(self):
        if not self._coupledBoundary:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Coupled Boundary'))
            return

        df = pd.DataFrame(self._fanCurve)
        if df.empty:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Edit Fan Curve'))
            return

        try:
            with coredb.CoreDB() as db:
                coupleTypeChanged = self._changeCoupledBoundary(db, self._coupledBoundary, self.BOUNDARY_TYPE)

                if self._fanCurveName.int == 0:
                    self._fanCurveName = uuid4()

                    self._writeConditions(db, self._xpath)
                    self._writeConditions(db, BoundaryDB.getXPath(self._coupledBoundary))

                super().accept()
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))

        Project.instance().fileDB().putDataFrame(uuidToNnstr(self._fanCurveName), df)

        if coupleTypeChanged:
            self.boundaryTypeChanged.emit(int(self._coupledBoundary))

    @qasync.asyncSlot()
    async def _reject(self):
        if self._fanCurveName.int == 0:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Be sure to edit Fan Curve'))
        else:
            self.reject()

    def _editFanCurve(self):
        self._dialog = PiecewiseLinearDialog(self, self.tr('Fan Curve'), 'Q', 'm3/s', ['P'], 'Pa', self._fanCurve)
        self._dialog.accepted.connect(self._fanCurveAccepted)
        self._dialog.open()

    def _fanCurveAccepted(self):
        self._fanCurve = self._dialog.getData()

    def _selectCoupledBoundary(self):
        if not self._boundarySelector:
            self._boundarySelector = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                                    BoundaryDB.getBoundarySelectorItemsForCoupling(self._bcid))
            self._boundarySelector.accepted.connect(self._coupledBoundaryAccepted)

        self._boundarySelector.open()

    def _coupledBoundaryAccepted(self):
        self._setCoupledBoundary(str(self._boundarySelector.selectedItem()))

    def _setCoupledBoundary(self, bcid):
        if bcid != '0':
            self._coupledBoundary = str(bcid)
            self._ui.coupledBoundary.setText(BoundaryDB.getBoundaryName(bcid))
        else:
            self._coupledBoundary = 0
            self._ui.coupledBoundary.setText('')

    def _writeConditions(self, db, xpath):
        db.setValue(xpath + '/fanCurveName', str(self._fanCurveName), self.tr("Fan Curve Name"))
