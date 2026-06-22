#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal

from widgets.selector_dialog import SelectorDialog, SelectorItem

from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.services.boundary.boundary_service import BoundaryService
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
        self._pairWithinGroup = BoundaryDB.getBoundaryType(self._bcid) != BoundaryType.THERMO_COUPLED_WALL

        self._coupleNameDisplay = None
        self._coupledBoundary = None

        self._boundarySelector = None

    def coupleBoundary(self):
        return self._coupledBoundary

    def _setCoupledBoundary(self, bcid):
        self._coupledBoundary = bcid
        if bcid == '0':
            self._coupleNameDisplay.clear()
        else:
            self._coupleNameDisplay.setText(
                BoundaryService.getBoundary(self._coupledBoundary).name if self._pairWithinGroup
                else BoundaryService.getBoundary(self._coupledBoundary).name.scoppedNmae)

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

    def _openCoupledBoundarySelector(self):
        if not self._boundarySelector:
            if self._pairWithinGroup:
                items = [SelectorItem(b.name, b.name, b.bcid)
                         for b in BoundaryService.getBoundariesIn(BoundaryService.getBoundary(self._bcid).rname)
                         if b.bcid != self._bcid]
            else:
                items = [SelectorItem(b.scoppedName, b.name, b.bcid)
                         for b in BoundaryService.getBoundaries() if b.bcid != self._bcid]

            self._boundarySelector = SelectorDialog(
                self, self.tr("Select Boundary"), self.tr("Select Boundary"), items)
            self._boundarySelector.accepted.connect(self._onCoupledBoundarySelected)

        self._boundarySelector.open()

    def _onCoupledBoundarySelected(self):
        self._setCoupledBoundary(self._boundarySelector.selectedItem())
