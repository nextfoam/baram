#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal

from coredb import coredb
from coredb.boundary_db import BoundaryType
from .boundary_type_picker_ui import Ui_BoundaryTypePicker


BOTTOM_MARGIN = 10


class BoundaryTypePicker(QWidget):
    picked = Signal(int, str)

    def __init__(self, bcid, point, screenHeight):
        super().__init__()
        self._ui = Ui_BoundaryTypePicker()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._bcid = bcid

        point.setY(min(screenHeight - self.height() - BOTTOM_MARGIN, point.y()))
        self.move(point)

        self.setWindowFlags(Qt.Popup)

        self._inletTypes = [
            BoundaryType.VELOCITY_INLET.value,
            BoundaryType.FLOW_RATE_INLET.value,
            BoundaryType.PRESSURE_INLET.value,
            BoundaryType.ABL_INLET.value,
            BoundaryType.OPEN_CHANNEL_INLET.value,
            BoundaryType.FREE_STREAM.value,
            BoundaryType.FAR_FIELD_RIEMANN.value,
            BoundaryType.SUBSONIC_INFLOW.value,
            BoundaryType.SUPERSONIC_INFLOW.value,
        ]

        self._outletTypes = [
            BoundaryType.PRESSURE_OUTLET.value,
            BoundaryType.OPEN_CHANNEL_OUTLET.value,
            BoundaryType.OUTFLOW.value,
            BoundaryType.SUBSONIC_OUTFLOW.value,
            BoundaryType.SUPERSONIC_OUTFLOW.value,
        ]

        self._wallTypes =  [
            BoundaryType.WALL.value,
            BoundaryType.THERMO_COUPLED_WALL.value,
            BoundaryType.POROUS_JUMP.value,
            BoundaryType.FAN.value,
        ]

        self._miscTypes = [
            BoundaryType.SYMMETRY.value,
            BoundaryType.INTERFACE.value,
            BoundaryType.EMPTY.value,
            BoundaryType.CYCLIC.value,
            BoundaryType.WEDGE.value,
        ]

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.inletTypes.currentRowChanged.connect(self._inletPick)
        self._ui.outletTypes.currentRowChanged.connect(self._outletPick)
        self._ui.wallTypes.currentRowChanged.connect(self._wallPick)
        self._ui.miscTypes.currentRowChanged.connect(self._miscPick)

    def _inletPick(self, row):
        self.picked.emit(self._bcid, self._inletTypes[row])
        self.hide()

    def _outletPick(self, row):
        self.picked.emit(self._bcid, self._outletTypes[row])
        self.hide()

    def _wallPick(self, row):
        self.picked.emit(self._bcid, self._wallTypes[row])
        self.hide()

    def _miscPick(self, row):
        self.picked.emit(self._bcid, self._miscTypes[row])
        self.hide()
