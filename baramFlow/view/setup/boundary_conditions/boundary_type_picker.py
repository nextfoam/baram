#!/usr/bin/env python
# -*- coding: utf-8 -*-


from enum import Enum, auto

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryType
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from .boundary_type_picker_ui import Ui_BoundaryTypePicker


BOTTOM_MARGIN = 10


class InletType(Enum):
    VELOCITY_INLET = 0
    FLOW_RATE_INLET = auto()
    PRESSURE_INLET = auto()
    ABL_INLET = auto()
    OPEN_CHANNEL_INLET = auto()
    FREE_STREAM = auto()
    FAR_FIELD_RIEMANN = auto()
    SUBSONIC_INFLOW = auto()
    SUPERSONIC_INFLOW = auto()


class OutletType(Enum):
    PRESSURE_OUTLET = 0
    OPEN_CHANNEL_OUTLET = auto()
    OUTFLOW = auto()
    SUBSONIC_OUTFLOW = auto()
    SUPERSONIC_OUTFLOW = auto()


class WallType(Enum):
    WALL = 0
    THERMO_COUPLED_WALL = auto()


class MiscType(Enum):
    SYMMETRY = 0
    INTERFACE = auto()
    EMPTY = auto()
    CYCLIC = auto()
    WEDGE = auto()
    POROUS_JUMP = auto()
    FAN = auto()


inletTypes = {
    InletType.VELOCITY_INLET.value: BoundaryType.VELOCITY_INLET.value,
    InletType.FLOW_RATE_INLET.value: BoundaryType.FLOW_RATE_INLET.value,
    InletType.PRESSURE_INLET.value: BoundaryType.PRESSURE_INLET.value,
    InletType.ABL_INLET.value: BoundaryType.ABL_INLET.value,
    InletType.OPEN_CHANNEL_INLET.value: BoundaryType.OPEN_CHANNEL_INLET.value,
    InletType.FREE_STREAM.value: BoundaryType.FREE_STREAM.value,
    InletType.FAR_FIELD_RIEMANN.value: BoundaryType.FAR_FIELD_RIEMANN.value,
    InletType.SUBSONIC_INFLOW.value: BoundaryType.SUBSONIC_INLET.value,
    InletType.SUPERSONIC_INFLOW.value: BoundaryType.SUPERSONIC_INFLOW.value,
}

outletTypes = {
    OutletType.PRESSURE_OUTLET.value: BoundaryType.PRESSURE_OUTLET.value,
    OutletType.OPEN_CHANNEL_OUTLET.value: BoundaryType.OPEN_CHANNEL_OUTLET.value,
    OutletType.OUTFLOW.value: BoundaryType.OUTFLOW.value,
    OutletType.SUBSONIC_OUTFLOW.value: BoundaryType.SUBSONIC_OUTFLOW.value,
    OutletType.SUPERSONIC_OUTFLOW.value: BoundaryType.SUPERSONIC_OUTFLOW.value,
}

wallTypes = {
    WallType.WALL.value: BoundaryType.WALL.value,
    WallType.THERMO_COUPLED_WALL.value: BoundaryType.THERMO_COUPLED_WALL.value,
}

miscTypes = {
    MiscType.SYMMETRY.value: BoundaryType.SYMMETRY.value,
    MiscType.INTERFACE.value: BoundaryType.INTERFACE.value,
    MiscType.EMPTY.value: BoundaryType.EMPTY.value,
    MiscType.CYCLIC.value: BoundaryType.CYCLIC.value,
    MiscType.WEDGE.value: BoundaryType.WEDGE.value,
    MiscType.POROUS_JUMP.value: BoundaryType.POROUS_JUMP.value,
    MiscType.FAN.value: BoundaryType.FAN.value,
}


def setListHeight(widget):
    widget.setFixedHeight(
        24 * len([widget.item(row) for row in range(widget.count()) if not widget.item(row).isHidden()]))


class BoundaryTypePicker(QWidget):
    picked = Signal(int, str)

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_BoundaryTypePicker()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._bcid = None

        self.setWindowFlags(Qt.Popup)

        isCompressible = GeneralDB.isCompressible()
        isEnergyOn = ModelsDB.isEnergyModelOn()
        isMultiphase = ModelsDB.isMultiphaseModelOn()
        isSpeciesOn = ModelsDB.isSpeciesModelOn()
        isMultiRegion = len(self._db.getRegions()) > 1

        if isCompressible or isMultiphase or isSpeciesOn:
            self._ui.inletTypes.item(InletType.ABL_INLET.value).setHidden(True)

        if isCompressible or isEnergyOn or not isMultiphase or isSpeciesOn or isMultiRegion:
            self._ui.inletTypes.item(InletType.OPEN_CHANNEL_INLET.value).setHidden(True)
            self._ui.outletTypes.item(OutletType.OPEN_CHANNEL_OUTLET.value).setHidden(True)

        if isCompressible or isMultiphase:
            self._ui.inletTypes.item(InletType.FREE_STREAM.value).setHidden(True)

        if not isCompressible or not isEnergyOn or isMultiphase or isSpeciesOn or isMultiRegion:
            self._ui.inletTypes.item(InletType.FAR_FIELD_RIEMANN.value).setHidden(True)
            self._ui.inletTypes.item(InletType.SUBSONIC_INFLOW.value).setHidden(True)
            self._ui.inletTypes.item(InletType.SUPERSONIC_INFLOW.value).setHidden(True)
            self._ui.outletTypes.item(OutletType.SUBSONIC_OUTFLOW.value).setHidden(True)
            self._ui.outletTypes.item(OutletType.SUPERSONIC_OUTFLOW.value).setHidden(True)

        setListHeight(self._ui.inletTypes)
        setListHeight(self._ui.outletTypes)
        setListHeight(self._ui.wallTypes)
        self.adjustSize()

        self._connectSignalsSlots()

    def open(self, bcid, point):
        self._bcid = bcid

        screenHeight = app.window.windowHandle().screen().availableSize().height()
        point.setY(min(screenHeight - self.height() - BOTTOM_MARGIN, point.y()))
        self.move(point)

        self.show()

    def _connectSignalsSlots(self):
        self._ui.inletTypes.currentRowChanged.connect(self._inletPick)
        self._ui.outletTypes.currentRowChanged.connect(self._outletPick)
        self._ui.wallTypes.currentRowChanged.connect(self._wallPick)
        self._ui.miscTypes.currentRowChanged.connect(self._miscPick)

    def _inletPick(self, row):
        self.picked.emit(self._bcid, inletTypes[row])
        self.hide()

    def _outletPick(self, row):
        self.picked.emit(self._bcid, outletTypes[row])
        self.hide()

    def _wallPick(self, row):
        self.picked.emit(self._bcid, wallTypes[row])
        self.hide()

    def _miscPick(self, row):
        self.picked.emit(self._bcid, miscTypes[row])
        self.hide()
