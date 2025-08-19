#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.models_db import ModelsDB
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

    @qasync.asyncSlot()
    async def accept(self):
        def reverse(layers):
            return ' '.join(layers.split()[::-1])

        if not self._coupledBoundary:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Coupled Boundary'))
            return

        try:
            with coredb.CoreDB() as db:
                coupleTypeChanged = self._changeCoupledBoundary(db, self._coupledBoundary, self.BOUNDARY_TYPE)

                if ModelsDB.isEnergyModelOn():
                    wallLayersXpath = self._xpath + '/thermoCoupledWall/temperature/wallLayers'
                    await self._ui.wallLayers.updateDB(db, wallLayersXpath)

                    coupleWallLayersXPath = (BoundaryDB.getXPath(self._coupledBoundary)
                                             + '/thermoCoupledWall/temperature/wallLayers')
                    db.setAttribute(coupleWallLayersXPath, 'disabled', 'true')
                    if self._ui.wallLayers.isChecked():
                        db.setValue(coupleWallLayersXPath + '/thicknessLayers',
                                    reverse(db.getValue(wallLayersXpath + '/thicknessLayers')))
                        db.setValue(coupleWallLayersXPath + '/thermalConductivityLayers',
                                    reverse(db.getValue(wallLayersXpath + '/thermalConductivityLayers')))

                super().accept()
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))

        if coupleTypeChanged:
            self.boundaryTypeChanged.emit(int(self._coupledBoundary))

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectCoupledBoundary)

    def _load(self):
        db = coredb.CoreDB()
        self._setCoupledBoundary(db.getValue(self._xpath + '/coupledBoundary'))

        if ModelsDB.isEnergyModelOn():
            self._ui.wallLayers.load(self._xpath + '/thermoCoupledWall/temperature/wallLayers')

            if (self._coupledBoundary
                and db.getAttribute(BoundaryDB.getXPath(self._coupledBoundary) + '/thermoCoupledWall/temperature/wallLayers', 'disabled') == 'false'):
                self._ui.wallLayers.setChecked(True)
        else:
            self._ui.temperatureGroup.hide()

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
            self._coupledBoundary = None
            self._ui.coupledBoundary.setText('')
