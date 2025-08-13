#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog


def changeBoundaryCouple(db, bcid, newCouple):
    xpath = BoundaryDB.getXPath(bcid) + '/coupledBoundary'
    currentCouple = db.getValue(xpath)
    if currentCouple != '0' and currentCouple != newCouple:
        db.setValue(BoundaryDB.getXPath(currentCouple) + '/coupledBoundary', '0')
    db.setValue(xpath, newCouple)


class CoupledBoundaryConditionDialog(ResizableDialog):
    boundaryTypeChanged = Signal(int)

    def __init__(self, parent, bcid):
        super().__init__(parent)

        self._bcid = bcid

    def _changeCoupledBoundary(self, db, cpid, bctype):
        changeBoundaryCouple(db, self._bcid, cpid)
        changeBoundaryCouple(db, cpid, self._bcid)

        xpath = BoundaryDB.getXPath(cpid) + '/physicalType'
        if db.getValue(xpath) != bctype.value:
            db.setValue(xpath, bctype.value)
            return True

        return False
