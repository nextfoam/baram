#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal

from baram.coredb import coredb
from baram.coredb.boundary_db import BoundaryDB
from baram.view.widgets.resizable_dialog import ResizableDialog


def changeBoundaryCouple(writer, bcid, newCouple):
    xpath = BoundaryDB.getXPath(bcid) + '/coupledBoundary'
    currentCouple = coredb.CoreDB().getValue(xpath)
    if currentCouple != '0' and currentCouple != newCouple:
        writer.append(BoundaryDB.getXPath(currentCouple) + '/coupledBoundary', '0', None)
    writer.append(xpath, newCouple, None)


class CoupledBoundaryConditionDialog(ResizableDialog):
    boundaryTypeChanged = Signal(int)

    def __init__(self, parent, bcid):
        super().__init__(parent)

        self._bcid = bcid

    def _changeCoupledBoundary(self, writer, cpid, bctype):
        changeBoundaryCouple(writer, self._bcid, cpid)
        changeBoundaryCouple(writer, cpid, self._bcid)

        db = coredb.CoreDB()
        xpath = BoundaryDB.getXPath(cpid) + '/physicalType'
        if db.getValue(xpath) != bctype.value:
            writer.append(xpath, bctype.value, None)
            return True

        return False
