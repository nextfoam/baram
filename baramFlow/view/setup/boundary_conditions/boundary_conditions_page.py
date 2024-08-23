#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QTreeWidgetItem, QMessageBox
from PySide6.QtCore import Qt

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryType, BoundaryDB
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME
from baramFlow.view.widgets.content_page import ContentPage
from .ABL_inlet_dialog import ABLInletDialog
from .boundary_conditions_page_ui import Ui_BoundaryConditionsPage
from .boundary_type_picker import BoundaryTypePicker
from .boundary_widget import BoundaryWidget
from .copy_dialog import CopyDialog
from .cyclic_dialog import CyclicDialog
from .fan_dialog import FanDialog
from .farfield_riemann_dialog import FarfieldRiemannDialog
from .flow_rate_inlet_dialog import FlowRateInletDialog
from .free_stream_dialog import FreeStreamDialog
from .interface_dialog import InterfaceDialog
from .open_channel_inlet_dialog import OpenChannelInletDialog
from .open_channel_outlet_dialog import OpenChannelOutletDialog
from .porous_jump_dialog import PorousJumpDialog
from .pressure_inlet_dialog import PressureInletDialog
from .pressure_outlet_dialog import PressureOutletDialog
from .subsonic_inlet_dialog import SubsonicInletDialog
from .subsonic_outflow_dialog import SubsonicOutflowDialog
from .supersonic_inflow_dialog import SupersonicInflowDialog
from .thermo_coupled_wall_dialog import ThermoCoupledWallDialog
from .velocity_inlet_dialog import VelocityInletDialog
from .wall_dialog import WallDialog


DIALOGS = {
    BoundaryType.VELOCITY_INLET.value: VelocityInletDialog,
    BoundaryType.FLOW_RATE_INLET.value: FlowRateInletDialog,
    BoundaryType.PRESSURE_INLET.value: PressureInletDialog,
    BoundaryType.ABL_INLET.value: ABLInletDialog,
    BoundaryType.OPEN_CHANNEL_INLET.value: OpenChannelInletDialog,
    BoundaryType.FREE_STREAM.value: FreeStreamDialog,
    BoundaryType.FAR_FIELD_RIEMANN.value: FarfieldRiemannDialog,
    BoundaryType.SUBSONIC_INLET.value: SubsonicInletDialog,
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


class BoundaryConditionsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_BoundaryConditionsPage()
        self._ui.setupUi(self)

        self._boundaries = {}

        self._dialog = None
        self._typePicker = None

        self._connectSignalsSlots()
        self._load()

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

        if app.vtkMesh():
            self._selectPickedBoundary()
            self._meshUpdated()

    def _connectSignalsSlots(self):
        # app.meshUpdated.connect(self._meshUpdated)
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.boundaries.currentItemChanged.connect(self._updateEditEnabled)
        self._ui.boundaries.itemDoubleClicked.connect(self._doubleClicked)
        self._ui.boundaries.itemChanged.connect(self._itemChanged)
        self._ui.boundaries.currentItemChanged.connect(self._currentBoundaryChanged)
        self._ui.copy.clicked.connect(self._copy)
        self._ui.edit.clicked.connect(self._edit)

    def _meshUpdated(self):
        app.vtkMesh().currentActorChanged.connect(self._selectPickedBoundary)

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
                childItem.setHidden(filterText not in boundaryWidget.bcname.lower())

    def _addBoundaryItems(self, parent, rname):
        db = coredb.CoreDB()
        boundaries = db.getBoundaryConditions(rname)
        for bcid, bcname, bctype in boundaries:
            item = QTreeWidgetItem(parent, bcid)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked)
            self._boundaries[bcid] = BoundaryWidget(rname, bcid, bcname, bctype, item)
            self._boundaries[bcid].rightClicked.connect(self._showTypePicker)
            self._ui.boundaries.setItemWidget(item, 1, self._boundaries[bcid])

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
            if item.checkState(column) == Qt.CheckState.Checked:
                app.vtkMesh().showActor(bcid)
            else:
                app.vtkMesh().hideActor(bcid)

    def _doubleClicked(self, item, column):
        if column:
            self._edit()

    def _changeBoundaryType(self, bcid, bctype):
        db = coredb.CoreDB()
        currentType = BoundaryDB.getBoundaryType(bcid)
        if currentType != bctype:
            xpath = BoundaryDB.getXPath(bcid)
            db.setValue(xpath + '/physicalType', bctype)
            self._boundaries[bcid].reloadType()
            self._updateEditEnabled()

            cpid = db.getValue(xpath + '/coupledBoundary')
            if cpid != '0':
                db.setValue(xpath + '/coupledBoundary', '0')
                db.setValue(BoundaryDB.getXPath(cpid) + '/coupledBoundary', '0')

            if BoundaryDB.needsCoupledBoundary(bctype):
                QMessageBox.information(
                    self, self.tr('Need to edit boundary condition'),
                    self.tr(f'The {BoundaryDB.dbBoundaryTypeToText(bctype)} boundary needs a coupled boundary.'))

            self._edit()

    def _boundaryTypeChanged(self, bcid):
        self._boundaries[bcid].reloadType()

    def _copy(self):
        self._dialog = CopyDialog(self)
        self._dialog.boundariesCopied.connect(self._refresh)
        self._dialog.open()

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
        self._typePicker = BoundaryTypePicker(self)
        self._typePicker.picked.connect(self._changeBoundaryType)
        self._typePicker.open(bcid, point)

    def _currentBoundaryChanged(self, current):
        app.vtkMesh().setCurrentId(current.type())

    def _selectPickedBoundary(self):
        if app.vtkMesh().currentId():
            self._ui.boundaries.setCurrentItem(self._boundaries[app.vtkMesh().currentId()].parent)
        else:
            self._ui.boundaries.clearSelection()

    def _refresh(self, boundaries):
        for bcid in boundaries:
            self._boundaries[bcid].reloadType()