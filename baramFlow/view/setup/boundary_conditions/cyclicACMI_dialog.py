#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

import qasync

from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from .cyclicACMI_dialog_ui import Ui_CyclicACMIDialog
from .coupled_boundary_condition_dialog import CoupledBoundaryConditionDialog


class CyclicACMIDialog(CoupledBoundaryConditionDialog):
    BOUNDARY_TYPE = BoundaryType.CYCLIC_ACMI
    RELATIVE_XPATH = '/cyclicACMI'

    def __init__(self, parent, bcid):
        super().__init__(parent, bcid)
        self._ui = Ui_CyclicACMIDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)
        self._coupledBoundary: Optional[str] = None
        self._fallbackBoundary: Optional[str] = None
        self._coupledDialog = None
        self._fallbackDialog = None

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def accept(self):
        if not self._coupledBoundary:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Coupled Boundary'))
            return

        if not self._fallbackBoundary:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Fallback Boundary'))
            return

        try:
            with coredb.CoreDB() as db:
                coupleTypeChanged = self._changeCoupledBoundary(db, self._coupledBoundary, self.BOUNDARY_TYPE)

                db.setValue(self._xpath + '/fallbackBoundary', self._fallbackBoundary)

                if coupleTypeChanged:
                    self.boundaryTypeChanged.emit(int(self._coupledBoundary))

                super().accept()
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))

    def _connectSignalsSlots(self):
        self._ui.selectCoupledBoundary.clicked.connect(self._selectCoupledBoundary)
        self._ui.selectFallbackBoundary.clicked.connect(self._selectFallbackBoundary)

    def _load(self):
        db = coredb.CoreDB()
        self._setCoupledBoundary(db.getValue(self._xpath + '/coupledBoundary'))
        self._setFallbackBoundary(db.getValue(self._xpath + '/fallbackBoundary'))

    def _selectCoupledBoundary(self):
        if not self._coupledDialog:
            self._coupledDialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                                 BoundaryDB.getBoundarySelectorItemsForCoupling(self._bcid))
            self._coupledDialog.accepted.connect(self._coupledBoundaryAccepted)

        self._coupledDialog.open()

    def _coupledBoundaryAccepted(self):
        self._setCoupledBoundary(self._coupledDialog.selectedItem())

    def _setCoupledBoundary(self, bcid):
        if bcid != '0':
            self._coupledBoundary = str(bcid)
            self._ui.coupledBoundary.setText(BoundaryDB.getBoundaryName(bcid))
        else:
            self._coupledBoundary = 0
            self._ui.coupledBoundary.setText('')

    def _selectFallbackBoundary(self):
        if not self._fallbackDialog:
            self._fallbackDialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                                  BoundaryDB.getBoundarySelectorItemsForCoupling(self._bcid))
            self._fallbackDialog.accepted.connect(self._fallbackBoundaryAccepted)

        self._fallbackDialog.open()

    def _fallbackBoundaryAccepted(self):
        self._setFallbackBoundary(self._fallbackDialog.selectedItem())

    def _setFallbackBoundary(self, bcid):
        if bcid != '0':
            self._fallbackBoundary = str(bcid)
            self._ui.fallbackBoundary.setText(BoundaryDB.getBoundaryName(bcid))
        else:
            self._fallbackBoundary = 0
            self._ui.fallbackBoundary.setText('')
