#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryType
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from .boundary_type_picker_ui import Ui_BoundaryTypePicker

BOTTOM_MARGIN = 10


def setListHeight(widget):
    widget.setFixedHeight(
        24 * len([widget.item(row) for row in range(widget.count()) if not widget.item(row).isHidden()]))


class BoundaryTypePicker(QWidget):
    picked = Signal(int, str)

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_BoundaryTypePicker()
        self._ui.setupUi(self)

        self._bcid = None

        self._types = {
            self._ui.velocityInlet:     BoundaryType.VELOCITY_INLET	 ,
            self._ui.flowRateInlet:     BoundaryType.FLOW_RATE_INLET	 ,
            self._ui.pressureInlet:     BoundaryType.PRESSURE_INLET	 ,
            self._ui.ABLInlet:          BoundaryType.ABL_INLET	     ,
            self._ui.openChannelInlet:  BoundaryType.OPEN_CHANNEL_INLET,
            self._ui.freeStream:        BoundaryType.FREE_STREAM	     ,
            self._ui.farFieldRiemann:   BoundaryType.FAR_FIELD_RIEMANN,
            self._ui.subsonicInlet:     BoundaryType.SUBSONIC_INLET	 ,
            self._ui.supersonicInflow:  BoundaryType.SUPERSONIC_INFLOW,
            self._ui.pressureOutlet:    BoundaryType.PRESSURE_OUTLET	 ,
            self._ui.openChannelOutlet: BoundaryType.OPEN_CHANNEL_OUTLET,
            self._ui.outflow:           BoundaryType.OUTFLOW	         ,
            self._ui.subsonicOutflow:   BoundaryType.SUBSONIC_OUTFLOW,
            self._ui.supersonicOutflow: BoundaryType.SUPERSONIC_OUTFLOW,
            self._ui.wall:              BoundaryType.WALL	         ,
            self._ui.thermoCoupledWall: BoundaryType.THERMO_COUPLED_WALL,
            self._ui.symmetry:          BoundaryType.SYMMETRY,
            self._ui.interface_:        BoundaryType.INTERFACE,
            self._ui.empty:             BoundaryType.EMPTY	     ,
            self._ui.cyclic:            BoundaryType.CYCLIC,
            self._ui.wedge:             BoundaryType.WEDGE	         ,
            self._ui.porousJump:        BoundaryType.POROUS_JUMP,
            self._ui.FAN:               BoundaryType.FAN,
        }

        self.setWindowFlags(Qt.Popup)

        isCompressible = GeneralDB.isCompressible()
        isEnergyOn = ModelsDB.isEnergyModelOn()
        isMultiphase = ModelsDB.isMultiphaseModelOn()
        isSpeciesOn = ModelsDB.isSpeciesModelOn()
        isMultiRegion = len(coredb.CoreDB().getRegions()) > 1

        if isCompressible or isMultiphase or isSpeciesOn:
            self._ui.ABLInlet.hide()

        if isCompressible or isEnergyOn or not isMultiphase or isSpeciesOn or isMultiRegion:
            self._ui.openChannelInlet.hide()
            self._ui.openChannelOutlet.hide()

        if isCompressible or isMultiphase:
            self._ui.freeStream.hide()

        if not isCompressible or not isEnergyOn or isMultiphase or isSpeciesOn or isMultiRegion:
            self._ui.farFieldRiemann.hide()
            self._ui.subsonicInlet.hide()
            self._ui.supersonicInflow.hide()
            self._ui.subsonicOutflow.hide()
            self._ui.supersonicOutflow.hide()

        self.adjustSize()

        self._connectSignalsSlots()

    def open(self, bcid, point):
        self._bcid = bcid

        screenHeight = app.window.windowHandle().screen().availableSize().height()
        point.setY(min(screenHeight - self.height() - BOTTOM_MARGIN, point.y()))
        self.move(point)

        self.show()

    def _connectSignalsSlots(self):
        self._ui.buttonGroup.buttonClicked.connect(self._typePicked)

    def _typePicked(self, button):
        self.picked.emit(self._bcid, self._types[button].value)
        self.hide()
