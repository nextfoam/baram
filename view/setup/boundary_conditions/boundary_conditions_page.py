#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QTableWidgetItem, QHeaderView, QComboBox
from PySide6.QtCore import Qt

from coredb import coredb
from .boundary_conditions_page_ui import Ui_BoundaryConditionsPage
from .velocity_inlet_dialog import VelocityInletDialog
from .flow_rate_inlet_dialog import FlowRateInletDialog
from .pressure_inlet_dialog import PressureInletDialog
from .pressure_outlet_dialog import PressureOutletDialog
from .ABL_inlet_dialog import ABLInletDialog
from .open_channel_inlet_dialog import OpenChannelInletDialog
from .open_channel_outlet_dialog import OpenChannelOutletDialog
from .free_stream_dialog import FreeStreamDialog
from .far_field_riemann_dialog import FarFieldRiemannDialog
from .subsonic_inflow_dialog import SubsonicInflowDialog
from .subsonic_outflow_dialog import SubsonicOutflowDialog
from .supersonic_inflow_dialog import SupersonicInflowDialog
from .wall_dialog import WallDialog
from .interface_dialog import InterfaceDialog
from .porous_jump_dialog import PorousJumpDialog
from .fan_dialog import FanDialog
from .cyclic_dialog import CyclicDialog


class BoundaryType(Enum):
    # Inlet
    VELOCITY_INLET	    = "velocityInlet"
    FLOW_RATE_INLET	    = "flowRateInlet"
    PRESSURE_INLET	    = "pressureInlet"
    ABL_INLET	        = "ablInlet"
    OPEN_CHANNEL_INLET  = "openChannelInlet"
    FREE_STREAM	        = "freeStream"
    FAR_FIELD_RIEMANN	= "farFieldRiemann"
    SUBSONIC_INFLOW	    = "subsonicInflow"
    SUPERSONIC_INFLOW	= "supersonicInflow"
    # Outlet
    PRESSURE_OUTLET	    = "pressureOutlet"
    OPEN_CHANNEL_OUTLET = "openChannelOutlet"
    OUTFLOW	            = "outflow"
    SUBSONIC_OUTFLOW	= "subsonicOutflow"
    SUPERSONIC_OUTFLOW	= "supersonicOutflow"
    # Wall
    WALL	            = "wall"
    THERMO_COUPLED_WALL	= "thermoCoupledWall"
    POROUS_JUMP	        = "porousJump"
    FAN	                = "fan"
    # Internal
    SYMMETRY	        = "symmetry"
    INTERFACE	        = "interface"
    EMPTY	            = "empty"
    CYCLIC	            = "cyclic"
    WEDGE	            = "wedge"


DIALOGS = {
    BoundaryType.VELOCITY_INLET: VelocityInletDialog,
    BoundaryType.FLOW_RATE_INLET: FlowRateInletDialog,
    BoundaryType.PRESSURE_INLET: PressureInletDialog,
    BoundaryType.ABL_INLET: ABLInletDialog,
    BoundaryType.OPEN_CHANNEL_INLET: OpenChannelInletDialog,
    BoundaryType.FREE_STREAM: FreeStreamDialog,
    BoundaryType.FAR_FIELD_RIEMANN: FarFieldRiemannDialog,
    BoundaryType.SUBSONIC_INFLOW: SubsonicInflowDialog,
    BoundaryType.SUPERSONIC_INFLOW: SupersonicInflowDialog,
    BoundaryType.PRESSURE_OUTLET: PressureOutletDialog,
    BoundaryType.OPEN_CHANNEL_OUTLET: OpenChannelOutletDialog,
    BoundaryType.OUTFLOW: None,
    BoundaryType.SUBSONIC_OUTFLOW: SubsonicOutflowDialog,
    BoundaryType.SUPERSONIC_OUTFLOW: None,
    BoundaryType.WALL: WallDialog,
    BoundaryType.THERMO_COUPLED_WALL: None,
    BoundaryType.POROUS_JUMP: PorousJumpDialog,
    BoundaryType.FAN: FanDialog,
    BoundaryType.SYMMETRY: None,
    BoundaryType.INTERFACE: InterfaceDialog,
    BoundaryType.EMPTY: None,
    BoundaryType.CYCLIC: CyclicDialog,
    BoundaryType.WEDGE: None,
}


class ListItemIndex(Enum):
    ID = 0
    NAME = auto()
    TYPE = auto()


class BoundaryConditionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_BoundaryConditionsPage()
        self._ui.setupUi(self)

        self._boundaries = None
        self._db = coredb.CoreDB()

        self._connectSignalsSlots()

        header = self._ui.list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self._load()

    def hideEvent(self, ev):
        if ev.spontaneous():
            return

    def _createComboBox(self, currentType):
        combo = QComboBox()

        # Inlet
        self._addComboItem(combo, currentType, BoundaryType.VELOCITY_INLET, self.tr("Velocity Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.FLOW_RATE_INLET, self.tr("Flow Rate Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.PRESSURE_INLET, self.tr("Pressure Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.ABL_INLET, self.tr("ABL Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.OPEN_CHANNEL_INLET, self.tr("Open Channel Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.FREE_STREAM, self.tr("Free Stream"))
        self._addComboItem(combo, currentType, BoundaryType.FAR_FIELD_RIEMANN, self.tr("Far-Field Riemann"))
        self._addComboItem(combo, currentType, BoundaryType.SUBSONIC_INFLOW, self.tr("Subsonic Inflow"))
        self._addComboItem(combo, currentType, BoundaryType.SUPERSONIC_INFLOW, self.tr("Supersonic Inflow"))
        # Outlet, BoundaryType
        self._addComboItem(combo, currentType, BoundaryType.PRESSURE_OUTLET, self.tr("Pressure Outlet"))
        self._addComboItem(combo, currentType, BoundaryType.OPEN_CHANNEL_OUTLET, self.tr("OpenChannel Outlet"))
        self._addComboItem(combo, currentType, BoundaryType.OUTFLOW, self.tr("Outflow"))
        self._addComboItem(combo, currentType, BoundaryType.SUBSONIC_OUTFLOW, self.tr("Subsonic Outflow"))
        self._addComboItem(combo, currentType, BoundaryType.SUPERSONIC_OUTFLOW, self.tr("Supersonic Outflow"))
        # Wall, BoundaryType
        self._addComboItem(combo, currentType, BoundaryType.WALL, self.tr("Wall"))
        self._addComboItem(combo, currentType, BoundaryType.THERMO_COUPLED_WALL, self.tr("Thermo-Coupled Wall"))
        self._addComboItem(combo, currentType, BoundaryType.POROUS_JUMP, self.tr("Porous Jump"))
        self._addComboItem(combo, currentType, BoundaryType.FAN, self.tr("FAN"))
        # Internal, BoundaryType
        self._addComboItem(combo, currentType, BoundaryType.SYMMETRY, self.tr("Symmetry"))
        self._addComboItem(combo, currentType, BoundaryType.INTERFACE, self.tr("Interface"))
        self._addComboItem(combo, currentType, BoundaryType.EMPTY, self.tr("Empty"))
        self._addComboItem(combo, currentType, BoundaryType.CYCLIC, self.tr("Cyclic"))
        self._addComboItem(combo, currentType, BoundaryType.WEDGE, self.tr("Wedge"))

        return combo

    def _addComboItem(self, combo, current, boundaryType, text):
        combo.addItem(text, boundaryType)
        if current == boundaryType.value:
            combo.setCurrentIndex(combo.count() - 1)

    def _connectSignalsSlots(self):
        self._ui.list.currentCellChanged.connect(self._boundarySelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)

    def _load(self):
        self._db.addBoundaryCondition("boundary1", "cyclic")
        self._db.addBoundaryCondition("boundary2", "patch")

        self._ui.list.clear()

        self._boundaries = self._db.getBoundaryConditions()
        self._ui.list.setRowCount(len(self._boundaries))

        for i in range(len(self._boundaries)):
            self._ui.list.setItem(i, 0, QTableWidgetItem(self._boundaries[i][ListItemIndex.NAME.value]))
            self._ui.list.setCellWidget(i, 1, self._createComboBox(self._boundaries[i][ListItemIndex.TYPE.value]))

    def _boundarySelected(self, row, column):
        dialogClass = DIALOGS[self._ui.list.cellWidget(row, 1).currentData(Qt.UserRole)]
        self._ui.edit.setEnabled(column == 0 and dialogClass is not None)

    def _edit(self):
        currentRow = self._ui.list.currentRow()
        dialogClass = DIALOGS[self._ui.list.cellWidget(currentRow, 1).currentData(Qt.UserRole)]
        if dialogClass is not None:
            self._dialog = dialogClass(self._boundaries[currentRow][ListItemIndex.ID.value])
            self._dialog.open()
