#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from view.widgets.resizable_dialog import ResizableDialog, ResizableForm
from .wall_dialog_ui import Ui_WallDialog


class WallDialog(ResizableDialog):
    class VELOCITY_CONDITION(Enum):
        NO_SLIP = 0
        SLIP = auto()
        MOVING_WALL = auto()
        ATMOSPHERIC_WALL = auto()
        TRANSLATIONAL_MOVING_WALL = auto()
        ROTATIONAL_MOVING_WALL = auto()

    class TEMPERATURE(Enum):
        ADIABATIC = 0
        CONSTANT_TEMPERATURE = auto()
        CONSTANT_HEAT_FLUX = auto()
        CONVECTION = auto()

    class TEMPERATURE_FORM_ROW(Enum):
        COMBOBOX = 0
        TEMPERATURE = auto()
        HEAT_FLUX = auto()
        HEAT_TRANSFER_COEFFICIENT = auto()
        FREE_STREAM_TEMPERATURE = auto()

    def __init__(self):
        super().__init__()
        self._ui = Ui_WallDialog()
        self._ui.setupUi(self)

        self._temperatureLayout = ResizableForm(self._ui.temperatureGroup.layout())

        self._setup()
        self._connectSignalsSlots()

        self._velocityConditionChanged(0)
        self._temperatureTypeChanged(0)

    def _setup(self):
        self._constantTemperatureGroup = [
            self.TEMPERATURE_FORM_ROW.TEMPERATURE.value,
        ]

        self._constantHeatFluxGroup = [
            self.TEMPERATURE_FORM_ROW.HEAT_FLUX.value,
        ]

        self._convectionGroup = [
            self.TEMPERATURE_FORM_ROW.HEAT_TRANSFER_COEFFICIENT.value,
            self.TEMPERATURE_FORM_ROW.FREE_STREAM_TEMPERATURE.value,
        ]

    def _connectSignalsSlots(self):
        self._ui.velocityCondition.currentIndexChanged.connect(self._velocityConditionChanged)
        self._ui.temperatureType.currentIndexChanged.connect(self._temperatureTypeChanged)

    def _velocityConditionChanged(self, index):
        self._ui.translationalMovingWall.setVisible(index == self.VELOCITY_CONDITION.TRANSLATIONAL_MOVING_WALL.value)
        self._ui.rotationalMovingWall.setVisible(index == self.VELOCITY_CONDITION.ROTATIONAL_MOVING_WALL.value)
        self._resizeDialog(self._ui.velocityGroup)

    def _temperatureTypeChanged(self, index):
        self._temperatureLayout.setRowsVisible(self._constantTemperatureGroup,
                              index == self.TEMPERATURE.CONSTANT_TEMPERATURE.value)
        self._temperatureLayout.setRowsVisible(self._constantHeatFluxGroup,
                              index == self.TEMPERATURE.CONSTANT_HEAT_FLUX.value)
        self._temperatureLayout.setRowsVisible(self._convectionGroup,
                              index == self.TEMPERATURE.CONVECTION.value)
        self._resizeDialog(self._ui.temperatureGroup)
