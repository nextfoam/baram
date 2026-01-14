#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal

from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
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

    def _changeCoupledBoundary(self, db, cpid, bctype: BoundaryType):
        changeBoundaryCouple(db, self._bcid, cpid)
        changeBoundaryCouple(db, cpid, self._bcid)

        xpath = BoundaryDB.getXPath(cpid)
        if db.getValue(xpath+'/physicalType') != bctype.value:
            db.setValue(xpath+'/physicalType', bctype.value)

            interactionType = DPMModelManager.getDefaultPatchInteractionType(bctype)
            db.setValue(xpath+'/patchInteraction/type', interactionType.value)

            return True

        return False
