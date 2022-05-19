#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QTableWidgetItem, QHeaderView, QComboBox
from PySide6.QtCore import Qt

from view.setup.boundary_conditions.boundary_conditions_page_ui import Ui_BoundaryConditionsPage
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


class BoundaryConditionsPage(QWidget):
    class BOUNDARY_TYPE(Enum):
        # Inlet
        VELOCITY_INLET = auto()
        FLOW_RATE_INLET = auto()
        PRESSURE_INLET = auto()
        ABL_INLET = auto()
        OPEN_CHANNEL_INLET = auto()
        FREE_STREAM = auto()
        FAR_FIELD_RIEMANN = auto()
        SUBSONIC_INFLOW = auto()
        SUPERSONIC_INFLOW = auto()
        # Outlet
        PRESSURE_OUTLET = auto()
        OPEN_CHANNEL_OUTLET = auto()
        OUTFLOW = auto()
        SUBSONIC_OUTFLOW = auto()
        SUPERSONIC_OUTFLOW = auto()
        # Wall
        WALL = auto()
        THERMO_COUPLED_WALL = auto()
        POROUS_JUMP = auto()
        FAN = auto()
        # Internal
        SYMMETRY = auto()
        INTERFACE = auto()
        EMPTY = auto()
        CYCLIC = auto()
        WEDGE = auto()

    def __init__(self):
        super().__init__()
        self._ui = Ui_BoundaryConditionsPage()
        self._ui.setupUi(self)

        self._boundaryTypes = None
        self._setup()
        self._connectSignalsSlots()

    def load(self):
        boundaries = [
            {
                "id": "b1",
                "name": "boundary1",
                "type": self.BOUNDARY_TYPE.FLOW_RATE_INLET,
            },
            {
                "id": "b2",
                "name": "boundary2",
                "type": self.BOUNDARY_TYPE.OPEN_CHANNEL_OUTLET,
            },
        ]

        self._ui.list.setRowCount(len(boundaries))
        header = self._ui.list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        for i in range(len(boundaries)):
            self._ui.list.setItem(i, 0, QTableWidgetItem(boundaries[i]["name"]))
            self._ui.list.setCellWidget(i, 1, self._createComboBox(boundaries[i]["type"]))

    def save(self):
        pass

    def _setup(self):
        self._boundaryTypes = {
            self.BOUNDARY_TYPE.VELOCITY_INLET: {
                "text": self.tr("Velocity Inlet"),
                "dialog": VelocityInletDialog
            },
            self.BOUNDARY_TYPE.FLOW_RATE_INLET: {
                "text": self.tr("Flow Rate Inlet"),
                "dialog": FlowRateInletDialog
            },
            self.BOUNDARY_TYPE.PRESSURE_INLET: {
                "text": self.tr("Pressure Inlet"),
                "dialog": PressureInletDialog
            },
            self.BOUNDARY_TYPE.ABL_INLET: {
                "text": self.tr("ABL Inlet"),
                "dialog": ABLInletDialog
            },
            self.BOUNDARY_TYPE.OPEN_CHANNEL_INLET: {
                "text": self.tr("Open Channel Inlet"),
                "dialog": OpenChannelInletDialog
            },
            self.BOUNDARY_TYPE.FREE_STREAM: {
                "text": self.tr("Free Stream"),
                "dialog": FreeStreamDialog
            },
            self.BOUNDARY_TYPE.FAR_FIELD_RIEMANN: {
                "text": self.tr("Far-Field Riemann"),
                "dialog": FarFieldRiemannDialog
            },
            self.BOUNDARY_TYPE.SUBSONIC_INFLOW: {
                "text": self.tr("Subsonic Inflow"),
                "dialog": SubsonicInflowDialog
            },
            self.BOUNDARY_TYPE.SUPERSONIC_INFLOW: {
                "text": self.tr("Supersonic Inflow"),
                "dialog": SupersonicInflowDialog
            },
            self.BOUNDARY_TYPE.PRESSURE_OUTLET: {
                "text": self.tr("Pressure Outlet"),
                "dialog": PressureOutletDialog
            },
            self.BOUNDARY_TYPE.OPEN_CHANNEL_OUTLET: {
                "text": self.tr("OpenChannel Outet"),
                "dialog": OpenChannelOutletDialog
            },
            self.BOUNDARY_TYPE.OUTFLOW: {
                "text": self.tr("Outflow"),
                "dialog": None
            },
            self.BOUNDARY_TYPE.SUBSONIC_OUTFLOW: {
                "text": self.tr("Subsonic Outflow"),
                "dialog": SubsonicOutflowDialog
            },
            self.BOUNDARY_TYPE.SUPERSONIC_OUTFLOW: {
                "text": self.tr("Supersonic Outflow"),
                "dialog": None
            },
            self.BOUNDARY_TYPE.WALL: {
                "text": self.tr("Wall"),
                "dialog": WallDialog
            },
            self.BOUNDARY_TYPE.THERMO_COUPLED_WALL: {
                "text": self.tr("Thermo-Coupled Wall"),
                "dialog": None
            },
            self.BOUNDARY_TYPE.POROUS_JUMP: {
                "text": self.tr("Porous Jump"),
                "dialog": PorousJumpDialog
            },
            self.BOUNDARY_TYPE.FAN: {
                "text": self.tr("FAN"),
                "dialog": FanDialog
            },
            self.BOUNDARY_TYPE.SYMMETRY: {
                "text": self.tr("Symmetry"),
                "dialog": None
            },
            self.BOUNDARY_TYPE.INTERFACE: {
                "text": self.tr("Interface"),
                "dialog": InterfaceDialog
            },
            self.BOUNDARY_TYPE.EMPTY: {
                "text": self.tr("Empty"),
                "dialog": None
            },
            self.BOUNDARY_TYPE.CYCLIC: {
                "text": self.tr("Cyclic"),
                "dialog": CyclicDialog
            },
            self.BOUNDARY_TYPE.WEDGE: {
                "text": self.tr("Wedge"),
                "dialog": None
            },
        }

    def _createComboBox(self, boundaryType):
        combo = QComboBox()
        for type_ in self._boundaryTypes:
            combo.addItem(self._boundaryTypes[type_]["text"], type_)
            if type_ == boundaryType:
                combo.setCurrentText(self._boundaryTypes[type_]["text"])

        return combo

    def _connectSignalsSlots(self):
        self._ui.list.currentCellChanged.connect(self._boundarySelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)

    def _boundarySelected(self, row, column):
        boundaryType = self._ui.list.cellWidget(self._ui.list.currentRow(), 1).currentData(Qt.UserRole)
        self._ui.edit.setEnabled(column == 0 and self._boundaryTypes[boundaryType]["dialog"] is not None)

    def _edit(self):
        boundaryType = self._ui.list.cellWidget(self._ui.list.currentRow(), 1).currentData(Qt.UserRole)
        dialogClass = self._boundaryTypes[boundaryType]["dialog"]
        if dialogClass is not None:
            dialog = self._boundaryTypes[boundaryType]["dialog"]()
            dialog.exec()
