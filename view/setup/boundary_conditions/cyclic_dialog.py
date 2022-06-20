#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.widgets.selector_dialog import SelectorDialog
from view.widgets.multi_selector_dialog import SelectorItem
from .cyclic_dialog_ui import Ui_CyclicDialog
from .boundary_db import BoundaryDB


class CyclicDialog(QDialog):
    RELATIVE_PATH = '/cyclic'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_CyclicDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)
        self._bcid = bcid
        self._coupledBoundary = None
        self._dialog = None

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_PATH

        writer = CoreDBWriter()
        if self._coupledBoundary is None:
            QMessageBox.critical(self, self.tr("Input Error"), "Select Coupled Boundary")
            return
        else:
            writer.append(path + '/coupledBoundary', self._coupledBoundary, self.tr("Coupled Boundary"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectCoupledBoundary)

    def _load(self):
        path = self._xpath + self.RELATIVE_PATH

        bcid = self._db.getValue(path + '/coupledBoundary')
        if bcid:
            self._setCoupledBoundary(bcid)

    def _selectCoupledBoundary(self):
        if self._dialog is None:
            self._dialog = SelectorDialog(
                self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                [
                    SelectorItem(f'{b.name} / {b.rname}', b.name, b.id)
                    for b in BoundaryDB.getCyclicAMIBoundaries(self._bcid)
                ])
            self._dialog.accepted.connect(self._coupledBoundaryAccepted)

        self._dialog.open()

    def _coupledBoundaryAccepted(self):
        self._setCoupledBoundary(str(self._dialog.selectedItem()))

    def _setCoupledBoundary(self, bcid):
        self._coupledBoundary = bcid
        self._ui.coupledBoundary.setText(f'{BoundaryDB.getBoundaryName(bcid)} / {BoundaryDB.getBoundaryRegion(bcid)}')
