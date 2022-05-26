#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog

from .wall_dialog_ui import Ui_WallDialog


class VelocityCondition(Enum):
    NO_SLIP = 0
    SLIP = auto()
    MOVING_WALL = auto()
    ATMOSPHERIC_WALL = auto()
    TRANSLATIONAL_MOVING_WALL = auto()
    ROTATIONAL_MOVING_WALL = auto()


class Temperature(Enum):
    ADIABATIC = 0
    CONSTANT_TEMPERATURE = auto()
    CONSTANT_HEAT_FLUX = auto()
    CONVECTION = auto()


class WallDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_WallDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

        self._velocityConditionChanged(0)
        self._temperatureTypeChanged(0)

    def _connectSignalsSlots(self):
        self._ui.velocityCondition.currentIndexChanged.connect(self._velocityConditionChanged)
        self._ui.temperatureType.currentIndexChanged.connect(self._temperatureTypeChanged)

    def _velocityConditionChanged(self, index):
        self._ui.translationalMovingWall.setVisible(index == VelocityCondition.TRANSLATIONAL_MOVING_WALL.value)
        self._ui.rotationalMovingWall.setVisible(index == VelocityCondition.ROTATIONAL_MOVING_WALL.value)

        QTimer.singleShot(0, lambda: self.adjustSize())

    def _temperatureTypeChanged(self, index):
        self._ui.constantTemperature.setVisible(index == Temperature.CONSTANT_TEMPERATURE.value)
        self._ui.constantHeatFlux.setVisible(index == Temperature.CONSTANT_HEAT_FLUX.value)
        self._ui.convection.setVisible(index == Temperature.CONVECTION.value)

        QTimer.singleShot(0, lambda: self.adjustSize())
