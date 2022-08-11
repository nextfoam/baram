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

    def __init__(self):
        super().__init__()
        self._ui = Ui_BoundaryTypePicker()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._bcid = None

        self.setWindowFlags(Qt.Popup)
        self.setStyleSheet('QPushButton {border-width: 0; background-color: transparent; text-align: left; padding: 4}'
                           'QPushButton:hover {background-color: rgba(0, 0, 0, 20)}')

        self._boundaryTypes = {
            self._ui.buttonGroup.id(self._ui.velocityInlet): BoundaryType.VELOCITY_INLET.value,
            self._ui.buttonGroup.id(self._ui.flowRateInlet): BoundaryType.FLOW_RATE_INLET.value,
            self._ui.buttonGroup.id(self._ui.pressureInlet): BoundaryType.PRESSURE_INLET.value,
            self._ui.buttonGroup.id(self._ui.ablInlet): BoundaryType.ABL_INLET.value,
            self._ui.buttonGroup.id(self._ui.openChannelInlet): BoundaryType.OPEN_CHANNEL_INLET.value,
            self._ui.buttonGroup.id(self._ui.freeStream): BoundaryType.FREE_STREAM.value,
            self._ui.buttonGroup.id(self._ui.farFieldRiemann): BoundaryType.FAR_FIELD_RIEMANN.value,
            self._ui.buttonGroup.id(self._ui.subsonicInflow): BoundaryType.SUBSONIC_INFLOW.value,
            self._ui.buttonGroup.id(self._ui.supersonicInflow): BoundaryType.SUPERSONIC_INFLOW.value,
            self._ui.buttonGroup.id(self._ui.pressureOutlet): BoundaryType.PRESSURE_OUTLET.value,
            self._ui.buttonGroup.id(self._ui.openChannelOutlet): BoundaryType.OPEN_CHANNEL_OUTLET.value,
            self._ui.buttonGroup.id(self._ui.outflow): BoundaryType.OUTFLOW.value,
            self._ui.buttonGroup.id(self._ui.subsonicOutflow): BoundaryType.SUBSONIC_OUTFLOW.value,
            self._ui.buttonGroup.id(self._ui.supersonicOutflow): BoundaryType.SUPERSONIC_OUTFLOW.value,
            self._ui.buttonGroup.id(self._ui.wall): BoundaryType.WALL.value,
            self._ui.buttonGroup.id(self._ui.thermoCoupledWall): BoundaryType.THERMO_COUPLED_WALL.value,
            self._ui.buttonGroup.id(self._ui.porousJump): BoundaryType.POROUS_JUMP.value,
            self._ui.buttonGroup.id(self._ui.fan): BoundaryType.FAN.value,
            self._ui.buttonGroup.id(self._ui.symmetry): BoundaryType.SYMMETRY.value,
            self._ui.buttonGroup.id(self._ui.interface_): BoundaryType.INTERFACE.value,
            self._ui.buttonGroup.id(self._ui.empty): BoundaryType.EMPTY.value,
            self._ui.buttonGroup.id(self._ui.cyclic): BoundaryType.CYCLIC.value,
            self._ui.buttonGroup.id(self._ui.wedge): BoundaryType.WEDGE.value,
        }

        self._connectSignalsSlots()

    @property
    def bcid(self):
        return self._bcid

    @bcid.setter
    def bcid(self, bcid):
        self._bcid = bcid

    def heightWithMargin(self):
        return self.height() + BOTTOM_MARGIN


    def _connectSignalsSlots(self):
        self._ui.buttonGroup.idClicked.connect(self._pick)

    def _pick(self, id_):
        self.picked.emit(self._bcid, self._boundaryTypes[id_])
        self.hide()
