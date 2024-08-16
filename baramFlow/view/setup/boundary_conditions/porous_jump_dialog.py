#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from .porous_jump_dialog_ui import Ui_PorousJumpDialog
from .coupled_boundary_condition_dialog import CoupledBoundaryConditionDialog


class PorousJumpDialog(CoupledBoundaryConditionDialog):
    BOUNDARY_TYPE = BoundaryType.POROUS_JUMP
    RELATIVE_XPATH = '/porousJump'

    def __init__(self, parent, bcid):
        super().__init__(parent, bcid)
        self._ui = Ui_PorousJumpDialog()
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
        self._writeConditions(writer, self._xpath + self.RELATIVE_XPATH)
        self._writeConditions(writer, BoundaryDB.getXPath(self._coupledBoundary) + self.RELATIVE_XPATH)

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
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.darcyCoefficient.setText(db.getValue(path + '/darcyCoefficient'))
        self._ui.inertialCoefficient.setText(db.getValue(path + '/inertialCoefficient'))
        self._ui.porousMedieThickness.setText(db.getValue(path + '/porousMediaThickness'))
        self._setCoupledBoundary(db.getValue(self._xpath + '/coupledBoundary'))

    def _selectCoupledBoundary(self):
        if not self._dialog:
            self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                          BoundaryDB.getBoundarySelectorItemsForCoupling(self._bcid))
            self._dialog.accepted.connect(self._coupledBoundaryAccepted)

        self._dialog.open()

    def _coupledBoundaryAccepted(self):
        self._setCoupledBoundary(str(self._dialog.selectedItem()))

    def _setCoupledBoundary(self, bcid):
        if bcid != '0':
            self._coupledBoundary = str(bcid)
            self._ui.coupledBoundary.setText(BoundaryDB.getBoundaryName(bcid))
        else:
            self._coupledBoundary = 0
            self._ui.coupledBoundary.setText('')

    def _writeConditions(self, writer, xpath):
        writer.append(xpath + '/darcyCoefficient', self._ui.darcyCoefficient.text(), self.tr('Darcy Coefficient'))
        writer.append(xpath + '/inertialCoefficient',
                      self._ui.inertialCoefficient.text(), self.tr('Inertial Coefficient'))
        writer.append(xpath + '/porousMediaThickness',
                      self._ui.porousMedieThickness.text(), self.tr('Porous Media Thickness'))
