#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.openfoam import parallel
from widgets.async_message_box import AsyncMessageBox

from baramFlow.app import app
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryType, BoundaryDB, GeometricalType
from baramFlow.coredb.project import Project
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME
from baramFlow.view.widgets.content_page import ContentPage
from .ABL_inlet_dialog import ABLInletDialog
from .boundary_conditions_page_ui import Ui_BoundaryConditionsPage
from .boundary_type_picker import BoundaryTypePicker
from .boundary_widget import BoundaryWidget
from .copy_dialog import CopyDialog
from .cyclic_dialog import CyclicDialog
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
    BoundaryType.WEDGE: None,
}


class BoundaryItem(QTreeWidgetItem):
    def __init__(self, parent, widget):
        super().__init__(parent, widget.bcid)

        self._widget = widget

        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(0, Qt.Checked)

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

        self._boundaries = {}

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
        self._ui.boundaries.currentItemChanged.connect(self._currentBoundaryChanged)
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
        self._ui.copy.setEnabled(not CaseManager().isActive())

    def _updateEditEnabled(self):
        item = self._ui.boundaries.currentItem()
        index = self._ui.boundaries.indexOfTopLevelItem(item)

        if index == -1:  # Not Top level item
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
            self._boundaries[bcid] = BoundaryItem(parent, widget)

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
        db = coredb.CoreDB()
        currentType = BoundaryDB.getBoundaryType(bcid)
        if currentType != bctype:
            xpath = BoundaryDB.getXPath(bcid)
            db.setValue(xpath + '/physicalType', bctype.value)
            self._boundaries[bcid].reloadType()
            self._updateEditEnabled()

            cpid = db.getValue(xpath + '/coupledBoundary')
            if cpid != '0':
                if (BoundaryDB.needsCoupledBoundary(bctype)
                        and BoundaryDB.getBoundaryType(cpid) == currentType
                        and bcid == int(db.getValue(BoundaryDB.getXPath(cpid) + '/coupledBoundary'))):
                    db.setValue(BoundaryDB.getXPath(cpid) + '/physicalType', bctype.value)
                    self._boundaries[int(cpid)].reloadType()
                else:
                    db.setValue(xpath + '/coupledBoundary', '0')
                    db.setValue(BoundaryDB.getXPath(cpid) + '/coupledBoundary', '0')
                    cpid = '0'

            if cpid == '0'and BoundaryDB.needsCoupledBoundary(bctype):
                if parallel.getNP() > 1 and BoundaryDB.getGeometryType(bctype) in [GeometricalType.CYCLIC, GeometricalType.CYCLIC_AMI]:
                    message = self.tr('1. This boundary type requires a coupled boundary. It is configured in the next dialog.\n\n' \
                                      '2. The current decomposed mesh could potentially be incompatible with this boundary type change.' \
                                      ' It is recommended to work in serial mode (single processor) when making this change.')
                else:
                    message = self.tr('This boundary type requires a coupled boundary.\nIt is configured in the next dialog.')

                await AsyncMessageBox().information(self, self.tr('Warning for ')+BoundaryDB.dbBoundaryTypeToText(bctype), message)

            interactionType = DPMModelManager.getDefaultPatchInteractionType(bctype)
            db.setValue(xpath + '/patchInteraction/type', interactionType.value)

            self._edit()

    def _boundaryTypeChanged(self, bcid):
        self._boundaries[bcid].reloadType()

    @qasync.asyncSlot()
    async def _copy(self):
        if item := self._ui.boundaries.currentItem():
            bcid = item.type()
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
            bcid = item.type()
            if bcid:
                bctype = self._boundaries[bcid].bctype()
                dialogClass = DIALOGS[bctype]
                if dialogClass:
                    self._dialog = dialogClass(self, str(bcid))
                    if BoundaryDB.needsCoupledBoundary(bctype):
                        self._dialog.boundaryTypeChanged.connect(self._boundaryTypeChanged)
                    self._dialog.open()

    def _showTypePicker(self, bcid, point):
        self._typePicker = BoundaryTypePicker(self)
        self._typePicker.picked.connect(self._changeBoundaryType)
        self._typePicker.open(bcid, point)

    def _currentBoundaryChanged(self, current):
        self._updateEditEnabled()
        app.meshModel().setCurrentId(current.type())

    def _selectPickedBoundary(self):
        if app.meshModel().currentId():
            self._ui.boundaries.setCurrentItem(self._boundaries[app.meshModel().currentId()])
        else:
            self._ui.boundaries.clearSelection()

    def _refresh(self, boundaries):
        for bcid in boundaries:
            self._boundaries[bcid].reloadType()