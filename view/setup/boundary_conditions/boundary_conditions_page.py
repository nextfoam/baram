#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QTreeWidgetItem, QMessageBox
from PySide6.QtCore import Qt

from app import app
from coredb import coredb
from coredb.boundary_db import BoundaryType, BoundaryDB
from .boundary_conditions_page_ui import Ui_BoundaryConditionsPage
from .velocity_inlet_dialog import VelocityInletDialog
from .flow_rate_inlet_dialog import FlowRateInletDialog
from .pressure_inlet_dialog import PressureInletDialog
from .pressure_outlet_dialog import PressureOutletDialog
from .ABL_inlet_dialog import ABLInletDialog
from .open_channel_inlet_dialog import OpenChannelInletDialog
from .open_channel_outlet_dialog import OpenChannelOutletDialog
from .free_stream_dialog import FreeStreamDialog
from .farfield_riemann_dialog import FarfieldRiemannDialog
from .subsonic_inflow_dialog import SubsonicInflowDialog
from .subsonic_outflow_dialog import SubsonicOutflowDialog
from .supersonic_inflow_dialog import SupersonicInflowDialog
from .thermo_coupled_wall_dialog import ThermoCoupledWallDialog
from .wall_dialog import WallDialog
from .interface_dialog import InterfaceDialog
from .porous_jump_dialog import PorousJumpDialog
from .fan_dialog import FanDialog
from .cyclic_dialog import CyclicDialog
from .boundary_widget import BoundaryWidget
from .boundary_type_picker import BoundaryTypePicker


DEFAULT_REGION_NAME = 'region0'

DIALOGS = {
    BoundaryType.VELOCITY_INLET.value: VelocityInletDialog,
    BoundaryType.FLOW_RATE_INLET.value: FlowRateInletDialog,
    BoundaryType.PRESSURE_INLET.value: PressureInletDialog,
    BoundaryType.ABL_INLET.value: ABLInletDialog,
    BoundaryType.OPEN_CHANNEL_INLET.value: OpenChannelInletDialog,
    BoundaryType.FREE_STREAM.value: FreeStreamDialog,
    BoundaryType.FAR_FIELD_RIEMANN.value: FarfieldRiemannDialog,
    BoundaryType.SUBSONIC_INFLOW.value: SubsonicInflowDialog,
    BoundaryType.SUPERSONIC_INFLOW.value: SupersonicInflowDialog,
    BoundaryType.PRESSURE_OUTLET.value: PressureOutletDialog,
    BoundaryType.OPEN_CHANNEL_OUTLET.value: OpenChannelOutletDialog,
    BoundaryType.OUTFLOW.value: None,
    BoundaryType.SUBSONIC_OUTFLOW.value: SubsonicOutflowDialog,
    BoundaryType.SUPERSONIC_OUTFLOW.value: None,
    BoundaryType.WALL.value: WallDialog,
    BoundaryType.THERMO_COUPLED_WALL.value: ThermoCoupledWallDialog,
    BoundaryType.POROUS_JUMP.value: PorousJumpDialog,
    BoundaryType.FAN.value: FanDialog,
    BoundaryType.SYMMETRY.value: None,
    BoundaryType.INTERFACE.value: InterfaceDialog,
    BoundaryType.EMPTY.value: None,
    BoundaryType.CYCLIC.value: CyclicDialog,
    BoundaryType.WEDGE.value: None,
}


class BoundaryConditionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_BoundaryConditionsPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._boundaries = {}

        self._dialog = None
        self._typePicker = None

        self._connectSignalsSlots()
        self.load()

    def save(self):
        return True

    def load(self):
        regions = self._db.getRegions()
        if len(regions) == 1 and not regions[0]:
            item = QTreeWidgetItem(self._ui.boundaries, [DEFAULT_REGION_NAME], 0)
            self._addBoundaryItems(item, '')
        else:
            for rname in regions:
                item = QTreeWidgetItem(self._ui.boundaries, [rname], 0)
                item.setFirstColumnSpanned(True)
                self._addBoundaryItems(item, rname)

        self._ui.boundaries.expandAll()
        self._ui.boundaries.resizeColumnToContents(0)

    def clear(self):
        self._ui.boundaries.clear()
        self._boundaries = {}

    def _connectSignalsSlots(self):
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.boundaries.currentItemChanged.connect(self._updateEditEnabled)
        self._ui.boundaries.doubleClicked.connect(self._edit)
        self._ui.boundaries.itemChanged.connect(self._itemChanged)
        self._ui.edit.clicked.connect(self._edit)

    def _filterChanged(self):
        filterText = self._ui.filter.text().lower()

        rnum = self._ui.boundaries.topLevelItemCount()
        for i in range(0, rnum):
            item = self._ui.boundaries.topLevelItem(i)
            bnum = item.childCount()
            self._ui.boundaries.invisibleRootItem()
            for j in range(0, bnum):
                childItem = item.child(j)
                boundaryWidget = self._ui.boundaries.itemWidget(childItem, 0)
                childItem.setHidden(filterText not in boundaryWidget.bcname.lower())

    def _addBoundaryItems(self, parent, rname):
        boundaries = self._db.getBoundaryConditions(rname)
        for bcid, bcname, bctype in boundaries:
            boundaryWidget = BoundaryWidget(rname, bcid, bcname, bctype)
            boundaryWidget.rightClicked.connect(self._showTypePicker)
            self._boundaries[bcid] = boundaryWidget

            item = QTreeWidgetItem(parent, bcid)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked)
            self._ui.boundaries.setItemWidget(item, 1, boundaryWidget)

    def _updateEditEnabled(self):
        bcid = self._ui.boundaries.currentItem().type()
        if bcid:
            bctype = self._boundaries[bcid].bctype
            if bctype and DIALOGS[bctype]:
                self._ui.edit.setEnabled(True)
                return

        self._ui.edit.setEnabled(False)

    def _itemChanged(self, item, column):
        bcid = item.type()
        if bcid:
            boundaryWidget = self._boundaries[bcid]
            if item.checkState(column) == Qt.CheckState.Checked:
                app.vtkMesh().showActor(boundaryWidget.rname, boundaryWidget.bcname)
            else:
                app.vtkMesh().hideActor(boundaryWidget.rname, boundaryWidget.bcname)

    def _changeBoundaryType(self, bcid, bctype):
        currentType = BoundaryDB.getBoundaryType(bcid)
        if currentType != bctype:
            xpath = BoundaryDB.getXPath(bcid)
            self._db.setValue(xpath + '/physicalType', bctype)
            self._boundaries[bcid].reloadType()
            self._updateEditEnabled()

            cpid = self._db.getValue(xpath + '/coupledBoundary')
            if cpid != '0':
                self._db.setValue(xpath + '/coupledBoundary', '0')
                self._db.setValue(BoundaryDB.getXPath(cpid) + '/coupledBoundary', '0')

            if BoundaryDB.needsCoupledBoundary(bctype):
                QMessageBox.information(
                    self, self.tr('Need to edit boundary condition'),
                    self.tr(f'The {BoundaryDB.dbBoundaryTypeToText(bctype)} boundary needs a coupled boundary.'))

            self._edit()

    def _boundaryTypeChanged(self, bcid):
        self._boundaries[bcid].reloadType()

    def _edit(self):
        item = self._ui.boundaries.currentItem()
        if item:
            bcid = item.type()
            if bcid:
                bctype = self._boundaries[bcid].bctype
                dialogClass = DIALOGS[bctype]
                if dialogClass:
                    self._dialog = dialogClass(self, str(bcid))
                    if BoundaryDB.needsCoupledBoundary(bctype):
                        self._dialog.boundaryTypeChanged.connect(self._boundaryTypeChanged)
                    self._dialog.open()

    def _showTypePicker(self, bcid, point):
        self._typePicker = BoundaryTypePicker(bcid, point,
                                              self.window().windowHandle().screen().availableSize().height())
        self._typePicker.picked.connect(self._changeBoundaryType)
        self._typePicker.show()

