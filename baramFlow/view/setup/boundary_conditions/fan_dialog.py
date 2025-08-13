#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project
from baramFlow.coredb.filedb import BcFileRole
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
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
        self._pqCurveFile = None
        self._pqCurveFileName = None

        self._boundarySelector = None
        self._dialog = None

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def accept(self):
        if not self._coupledBoundary:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Coupled Boundary'))
            return

        try:
            xpath = self._xpath + self.RELATIVE_XPATH
            fileDB = Project.instance().fileDB()

            oldFanCurveFile = None
            fanCurveFileKey = None
            if self._pqCurveFile:
                oldFanCurveFile = coredb.CoreDB().getValue(xpath + '/fanCurveFile')
                fanCurveFileKey = fileDB.putBcFile(self._bcid, BcFileRole.BC_FAN_CURVE, self._pqCurveFile)
            elif not self._pqCurveFileName:
                await AsyncMessageBox().information(
                    self, self.tr("Input Error"), self.tr("Select Fan P-Q Curve File."))
                return False

            with coredb.CoreDB() as db:
                coupleTypeChanged = self._changeCoupledBoundary(db, self._coupledBoundary, self.BOUNDARY_TYPE)

                self._writeConditions(db, xpath, fanCurveFileKey)
                self._writeConditions(db, BoundaryDB.getXPath(self._coupledBoundary) + self.RELATIVE_XPATH, fanCurveFileKey)

                if fanCurveFileKey and oldFanCurveFile:
                    fileDB.delete(oldFanCurveFile)

                super().accept()
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))

        if coupleTypeChanged:
            self.boundaryTypeChanged.emit(int(self._coupledBoundary))

    def _connectSignalsSlots(self):
        self._ui.fanPQCurveFileSelect.clicked.connect(self._selectFanPQCurveFile)
        self._ui.coupledBoundarySelect.clicked.connect(self._selectCoupledBoundary)

    def _load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._setCoupledBoundary(db.getValue(self._xpath + '/coupledBoundary'))
        self._pqCurveFileName = Project.instance().fileDB().getUserFileName(db.getValue(xpath + '/fanCurveFile'))
        self._ui.fanPQCurveFileName.setText(self._pqCurveFileName)

    def _selectFanPQCurveFile(self):
        self._dialog = QFileDialog(self, self.tr('Select CSV File'), '', 'CSV (*.csv)')
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._dialog.accepted.connect(self._fanPQCurveFileSelected)
        self._dialog.open()

    def _selectCoupledBoundary(self):
        if not self._boundarySelector:
            self._boundarySelector = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                                    BoundaryDB.getBoundarySelectorItemsForCoupling(self._bcid))
            self._boundarySelector.accepted.connect(self._coupledBoundaryAccepted)

        self._boundarySelector.open()

    def _coupledBoundaryAccepted(self):
        self._setCoupledBoundary(str(self._boundarySelector.selectedItem()))

    def _fanPQCurveFileSelected(self):
        if files := self._dialog.selectedFiles():
            self._pqCurveFile = Path(files[0])
            self._ui.fanPQCurveFileName.setText(self._pqCurveFile.name)

    def _setCoupledBoundary(self, bcid):
        if bcid != '0':
            self._coupledBoundary = str(bcid)
            self._ui.coupledBoundary.setText(BoundaryDB.getBoundaryName(bcid))
        else:
            self._coupledBoundary = 0
            self._ui.coupledBoundary.setText('')

    def _writeConditions(self, db, xpath, fanCurveFileKey):
        if fanCurveFileKey:
            db.setValue(xpath + '/fanCurveFile', fanCurveFileKey)
