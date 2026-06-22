#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

from widgets.async_message_box import AsyncMessageBox

from baramFlow.app import app
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryType, BoundaryDB, GeometricalType
from baramFlow.coredb.project import Project
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME
from baramFlow.openfoam import parallel
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.view.widgets.content_page import ContentPage
from .ABL_inlet_dialog import ABLInletDialog
from .boundary_conditions_page_ui import Ui_BoundaryConditionsPage
from .boundary_type_picker import BoundaryTypePicker
from .boundary_widget import BoundaryWidget
from .copy_dialog import CopyDialog
from .cyclic_dialog import CyclicDialog
from .cyclicACMI_dialog import CyclicACMIDialog
from .exhaust_fan_dialog import ExhaustFanDialog
from .fan_dialog import FanDialog
from .farfield_riemann_dialog import FarfieldRiemannDialog
from .flow_rate_inlet_dialog import FlowRateInletDialog
from .flow_rate_outlet_dialog import FlowRateOutletDialog
from .free_stream_dialog import FreeStreamDialog
from .interface_dialog import InterfaceDialog
from .open_channel_inlet_dialog import OpenChannelInletDialog
from .open_channel_outlet_dialog import OpenChannelOutletDialog
from .porous_jump_dialog import PorousJumpDialog
from .pressure_inlet_dialog import PressureInletDialog
from .pressure_outlet_dialog import PressureOutletDialog
from .intake_fan_dialog import IntakeFanDialog
from .subsonic_inlet_dialog import SubsonicInletDialog
from .subsonic_outflow_dialog import SubsonicOutflowDialog
from .supersonic_inflow_dialog import SupersonicInflowDialog
from .thermo_coupled_wall_dialog import ThermoCoupledWallDialog
from .velocity_inlet_dialog import VelocityInletDialog
from .wall_dialog import WallDialog


DIALOGS = {
    BoundaryType.VELOCITY_INLET: VelocityInletDialog,
    BoundaryType.FLOW_RATE_INLET: FlowRateInletDialog,
    BoundaryType.PRESSURE_INLET: PressureInletDialog,
    BoundaryType.INTAKE_FAN: IntakeFanDialog,
    BoundaryType.ABL_INLET: ABLInletDialog,
    BoundaryType.OPEN_CHANNEL_INLET: OpenChannelInletDialog,
    BoundaryType.FREE_STREAM: FreeStreamDialog,
    BoundaryType.FAR_FIELD_RIEMANN: FarfieldRiemannDialog,
    BoundaryType.SUBSONIC_INLET: SubsonicInletDialog,
    BoundaryType.SUPERSONIC_INFLOW: SupersonicInflowDialog,
    BoundaryType.FLOW_RATE_OUTLET: FlowRateOutletDialog,
    BoundaryType.PRESSURE_OUTLET: PressureOutletDialog,
    BoundaryType.EXHAUST_FAN: ExhaustFanDialog,
    BoundaryType.OPEN_CHANNEL_OUTLET: OpenChannelOutletDialog,
    BoundaryType.OUTFLOW: None,
    BoundaryType.SUBSONIC_OUTFLOW: SubsonicOutflowDialog,
    BoundaryType.SUPERSONIC_OUTFLOW: None,
    BoundaryType.WALL: WallDialog,
    BoundaryType.THERMO_COUPLED_WALL: ThermoCoupledWallDialog,
    BoundaryType.POROUS_JUMP: PorousJumpDialog,
    BoundaryType.FAN: FanDialog,
    BoundaryType.SYMMETRY: None,
    BoundaryType.INTERFACE: InterfaceDialog,
    BoundaryType.EMPTY: None,
    BoundaryType.CYCLIC: CyclicDialog,
    BoundaryType.CYCLIC_ACMI: CyclicACMIDialog,
    BoundaryType.WEDGE: None,
}


class BoundaryItem(QTreeWidgetItem):
    def __init__(self, parent, widget):
        super().__init__(parent, widget.bcid)

        self._widget = widget

        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.setCheckState(0, Qt.CheckState.Checked)

        self.treeWidget().setItemWidget(self, 1, widget)

    def __lt__(self, other):
        return self._widget.bcname().lower() < other._widget.bcname().lower()

    def bctype(self):
        return self._widget.type()

    def reloadType(self):
        self._widget.setType(BoundaryDB.getBoundaryType(self.type()))


class BoundaryConditionsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_BoundaryConditionsPage()
        self._ui.setupUi(self)

        self._boundaries: dict[str: BoundaryItem] = {}

        self._dialog = None
        self._typePicker = None

        self._ui.boundaries.setSortingEnabled(True)
        self._ui.boundaries.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        self._ui.edit.setEnabled(False)

        self._connectSignalsSlots()
        self._updateCopyEnabled()
        self._load()

    def closeEvent(self, event):
        self._disconnectSignalsSlots()

        super().closeEvent(event)

    def _connectSignalsSlots(self):
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.boundaries.itemDoubleClicked.connect(self._doubleClicked)
        self._ui.boundaries.itemChanged.connect(self._itemChanged)
        self._ui.boundaries.currentItemChanged.connect(self._onSelectedBoundaryChanged)
        self._ui.copy.clicked.connect(self._copy)
        self._ui.edit.clicked.connect(self._edit)

        Project.instance().solverStatusChanged.connect(self._updateCopyEnabled)

    def _disconnectSignalsSlots(self):
        Project.instance().solverStatusChanged.disconnect(self._updateCopyEnabled)

    def _load(self):
        db = coredb.CoreDB()
        regions = db.getRegions()
        if len(regions) == 1 and not regions[0]:
            item = QTreeWidgetItem(self._ui.boundaries, [DEFAULT_REGION_NAME], 0)
            item.setFirstColumnSpanned(True)
            self._addBoundaryItems(item, '')
        else:
            for rname in regions:
                item = QTreeWidgetItem(self._ui.boundaries, [rname], 0)
                item.setFirstColumnSpanned(True)
                self._addBoundaryItems(item, rname)

        self._ui.boundaries.expandAll()
        self._ui.boundaries.resizeColumnToContents(0)

        if app.meshModel():
            self._selectPickedBoundary()
            self._meshUpdated()

    def _updateCopyEnabled(self):
        self._ui.copy.setEnabled(not CaseManager().isActive() and self._ui.boundaries.currentItem() is not None)

    def _updateEditEnabled(self):
        item = self._ui.boundaries.currentItem()
        index = self._ui.boundaries.indexOfTopLevelItem(item)

        if index == -1 and item is not None:  # Not Top level item
            bctype = item.bctype()
            if bctype and DIALOGS[bctype]:
                self._ui.edit.setEnabled(True)
                return

        self._ui.edit.setEnabled(False)

    def _meshUpdated(self):
        app.meshModel().currentActorChanged.connect(self._selectPickedBoundary)

    def _filterChanged(self):
        filterText = self._ui.filter.text().lower()

        rnum = self._ui.boundaries.topLevelItemCount()
        for i in range(0, rnum):
            item = self._ui.boundaries.topLevelItem(i)
            bnum = item.childCount()
            self._ui.boundaries.invisibleRootItem()
            for j in range(0, bnum):
                childItem = item.child(j)
                boundaryWidget = self._ui.boundaries.itemWidget(childItem, 1)
                childItem.setHidden(filterText not in boundaryWidget.bcname().lower())

    def _addBoundaryItems(self, parent, rname):
        db = coredb.CoreDB()
        boundaries = db.getBoundaryConditions(rname)
        for bcid, bcname, bctype in boundaries:
            widget = BoundaryWidget(rname, bcid, bcname, BoundaryType(bctype))
            widget.rightClicked.connect(self._showTypePicker)
            self._boundaries[str(bcid)] = BoundaryItem(parent, widget)

    def _itemChanged(self, item, column):
        bcid = item.type()
        if bcid:
            if item.checkState(column) == Qt.CheckState.Checked:
                app.meshModel().showActor(bcid)
            else:
                app.meshModel().hideActor(bcid)

    def _doubleClicked(self, item, column):
        if column:
            self._edit()

    @qasync.asyncSlot()
    async def _changeBoundaryType(self, bcid, bctype: BoundaryType):
        oldType = BoundaryService.getBoundary(bcid).bctype
        if oldType != bctype:
            BoundaryService.updateBoundaryType(bcid, bctype)

            boundary = BoundaryService.getBoundary(bcid).boundary
            self._boundaries[bcid].reloadType()
            self._updateEditEnabled()

            if boundary.coupledBoundary != '0':
                self._boundaries[boundary.coupledBoundary].reloadType()
            elif BoundaryDB.needsCoupledBoundary(bctype):
                if parallel.getNP() > 1 and BoundaryDB.getGeometryType(bctype) in [GeometricalType.CYCLIC, GeometricalType.CYCLIC_AMI]:
                    message = self.tr('1. This boundary type requires a coupled boundary. It is configured in the next dialog.\n\n' \
                                      '2. The current decomposed mesh could potentially be incompatible with this boundary type change.' \
                                      ' It is recommended to work in serial mode (single processor) when making this change.')
                else:
                    message = self.tr('This boundary type requires a coupled boundary.\nIt is configured in the next dialog.')

                await AsyncMessageBox().information(self, self.tr('Warning for ')+BoundaryDB.dbBoundaryTypeToText(bctype), message)

            self._edit()

    def _onCouplingBoundaryEdited(self):
        self._boundaries[self._dialog.coupleBoundary()].reloadType()

    @qasync.asyncSlot()
    async def _copy(self):
        if item := self._ui.boundaries.currentItem():
            bcid = str(item.type())
            bctype = self._boundaries[bcid].bctype()
            if BoundaryDB.needsCoupledBoundary(bctype):
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'),
                    self.tr('{} boundary conditions cannot be copied.'.format(BoundaryDB.dbBoundaryTypeToText(bctype))))
                return

            self._dialog = CopyDialog(self, bcid)
            self._dialog.boundariesCopied.connect(self._refresh)
            self._dialog.open()
        else:
            await AsyncMessageBox().information(
                self, self.tr('Input Error'), self.tr('Select a source boundary to copy its conditions'))


    def _edit(self):
        if item := self._ui.boundaries.currentItem():
            bcid = str(item.type())
            if bcid:
                bctype = self._boundaries[bcid].bctype()
                dialogClass = DIALOGS[bctype]
                if dialogClass:
                    self._dialog = dialogClass(self, str(bcid))
                    if BoundaryDB.needsCoupledBoundary(bctype):
                        self._dialog.accepted.connect(self._onCouplingBoundaryEdited)
                    self._dialog.open()

    def _showTypePicker(self, bcid, point):
        self._typePicker = BoundaryTypePicker(self)
        self._typePicker.picked.connect(self._changeBoundaryType)
        self._typePicker.open(str(bcid), point)

    def _onSelectedBoundaryChanged(self, current):
        self._updateEditEnabled()
        self._updateCopyEnabled()

        if self._ui.boundaries.currentItem() is not None:
            app.meshModel().setCurrentId(current.type())

    def _selectPickedBoundary(self):
        if app.meshModel().currentId():
            self._ui.boundaries.setCurrentItem(self._boundaries[str(app.meshModel().currentId())])
        else:
            self._ui.boundaries.setCurrentItem(None)

    def _refresh(self, boundaries):
        for bcid in boundaries:
            self._boundaries[str(bcid)].reloadType()