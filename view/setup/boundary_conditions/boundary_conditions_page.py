#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

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
from .farfield_riemann_dialog import FarfieldRiemannDialog
from .subsonic_inflow_dialog import SubsonicInflowDialog
from .subsonic_outflow_dialog import SubsonicOutflowDialog
from .supersonic_inflow_dialog import SupersonicInflowDialog
from .wall_dialog import WallDialog
from .interface_dialog import InterfaceDialog
from .porous_jump_dialog import PorousJumpDialog
from .fan_dialog import FanDialog
from .cyclic_dialog import CyclicDialog
from .boundary_db import BoundaryType
from .region_widget import RegionWidget

DIALOGS = {
    BoundaryType.VELOCITY_INLET: VelocityInletDialog,
    BoundaryType.FLOW_RATE_INLET: FlowRateInletDialog,
    BoundaryType.PRESSURE_INLET: PressureInletDialog,
    BoundaryType.ABL_INLET: ABLInletDialog,
    BoundaryType.OPEN_CHANNEL_INLET: OpenChannelInletDialog,
    BoundaryType.FREE_STREAM: FreeStreamDialog,
    BoundaryType.FAR_FIELD_RIEMANN: FarfieldRiemannDialog,
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


class BoundaryConditionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_BoundaryConditionsPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._regions = {}
        self._currentRegion = None

        self._connectSignalsSlots()

        self._load()

    def hideEvent(self, ev):
        if ev.spontaneous():
            return super().hideEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.edit.clicked.connect(self._edit)

    def _load(self):
        layout = self._ui.regions.layout()
        regions = self._db.getRegions()
        for r in regions:
            self._regions[r] = RegionWidget(r)
            layout.addWidget(self._regions[r])
            self._regions[r].regionSelected.connect(self._regionSelected)
            self._regions[r].boundaryTypeChanged.connect(self._boundaryTypeChanged)
            self._regions[r].boundaryDoubleClicked.connect(self._edit)

    def _regionSelected(self, rname):
        if self._currentRegion is not None:
            if rname == self._currentRegion.rname:
                return
            self._currentRegion.clearSelection()

        self._currentRegion = self._regions[rname]
        self._ui.edit.setEnabled(True)

    def _boundaryTypeChanged(self, boundaryType):
        self._ui.edit.setEnabled(DIALOGS[boundaryType] is not None)

    def _edit(self):
        dialogClass = DIALOGS[self._currentRegion.currentBoundaryType()]
        if dialogClass is not None:
            self._dialog = dialogClass(self, self._currentRegion.currentBoundaryId())
            self._dialog.open()
