#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project
from baramFlow.coredb.filedb import BcFileRole
from baramFlow.coredb.coredb_writer import CoreDBWriter
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

    def accept(self):
        if not self._coupledBoundary:
            QMessageBox.critical(self, self.tr('Input Error'), self.tr('Select Coupled Boundary'))
            return

        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH
        fileDB = Project.instance().fileDB()

        oldFanCurveFile = None
        fanCurveFileKey = None
        if self._pqCurveFile:
            oldFanCurveFile = db.getValue(xpath + '/fanCurveFile')
            fanCurveFileKey = fileDB.putBcFile(self._bcid, BcFileRole.BC_FAN_CURVE, self._pqCurveFile)
        elif not self._pqCurveFileName:
            QMessageBox.critical(self, self.tr("Input Error"), self.tr("Select Fan P-Q Curve File."))
            return False

        writer = CoreDBWriter()
        coupleTypeChanged = self._changeCoupledBoundary(writer, self._coupledBoundary, self.BOUNDARY_TYPE)
        self._writeConditions(writer, xpath, fanCurveFileKey)
        self._writeConditions(writer, BoundaryDB.getXPath(self._coupledBoundary) + self.RELATIVE_XPATH, fanCurveFileKey)

        errorCount = writer.write()
        if errorCount > 0:
            if fanCurveFileKey:
                fileDB.delete(fanCurveFileKey)

            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())
        else:
            if fanCurveFileKey and oldFanCurveFile:
                fileDB.delete(oldFanCurveFile)

            if coupleTypeChanged:
                self.boundaryTypeChanged.emit(int(self._coupledBoundary))

            super().accept()

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

    def _writeConditions(self, writer, xpath, fanCurveFileKey):
        if fanCurveFileKey:
            writer.append(xpath + '/fanCurveFile', fanCurveFileKey, None)
