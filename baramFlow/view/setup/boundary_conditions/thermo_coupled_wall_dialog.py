#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from .thermo_coupled_wall_dialog_ui import Ui_ThermoCoupledWallDailog
from .coupled_boundary_condition_dialog import CoupledBoundaryConditionDialog


class ThermoCoupledWallDialog(CoupledBoundaryConditionDialog):
    BOUNDARY_TYPE = BoundaryType.THERMO_COUPLED_WALL
    RELATIVE_XPATH = '/thermoCoupledWall'

    def __init__(self, parent, bcid):
        super().__init__(parent, bcid)
        self._ui = Ui_ThermoCoupledWallDailog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)
        self._coupledBoundary = None
        self._dialog = None

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        if not self._coupledBoundary:
            QMessageBox.critical(self, self.tr('Input Error'), self.tr('Select Coupled Boundary'))
            return

        writer = CoreDBWriter()
        coupleTypeChanged = self._changeCoupledBoundary(writer, self._coupledBoundary, self.BOUNDARY_TYPE)

        errorCount = writer.write()
        if errorCount == 0:
            if coupleTypeChanged:
                self.boundaryTypeChanged.emit(int(self._coupledBoundary))

            super().accept()
        else:
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectCoupledBoundary)

    def _load(self):
        db = coredb.CoreDB()
        self._setCoupledBoundary(db.getValue(self._xpath + '/coupledBoundary'))

    def _selectCoupledBoundary(self):
        if not self._dialog:
            self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                          BoundaryDB.getBoundarySelectorItemsForCoupling(self._bcid, False))
            self._dialog.accepted.connect(self._coupledBoundaryAccepted)

        self._dialog.open()

    def _coupledBoundaryAccepted(self):
        self._setCoupledBoundary(str(self._dialog.selectedItem()))

    def _setCoupledBoundary(self, bcid):
        if bcid != '0':
            self._coupledBoundary = str(bcid)
            self._ui.coupledBoundary.setText(BoundaryDB.getBoundaryText(bcid))
        else:
            self._coupledBoundary = 0
            self._ui.coupledBoundary.setText('')
