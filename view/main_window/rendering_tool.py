#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QObject, Signal


class RenderingMode(Enum):
    DISPLAY_MODE_FEATURE        = 0
    DISPLAY_MODE_SURFACE        = auto()
    DISPLAY_MODE_SURFACE_EDGE   = auto()


class RenderingTool(QObject):
    renderingModeChanged = Signal(RenderingMode)

    def __init__(self, ui):
        super().__init__()

        self._view = ui.renderingView

        ui.plusX.clicked.connect(self._view.turnTowardX)
        ui.plusY.clicked.connect(self._view.tunTowardY)
        ui.plusZ.clicked.connect(self._view.turnTowardZ)
        ui.minusX.clicked.connect(self._view.turnAwayFromX)
        ui.minusY.clicked.connect(self._view.turnAwayFromY)
        ui.minusZ.clicked.connect(self._view.turnAwayFromZ)
        ui.axis.toggled.connect(self._view.setAxisVisible)
        ui.cubeAxis.toggled.connect(self._view.setCubeAxisVisible)
        ui.fit.clicked.connect(self._view.fitCamera)
        ui.perspective.toggled.connect(self._view.setPerspective)
        ui.rotate.clicked.connect(self._view.rollCamera)
        ui.renderingMode.currentIndexChanged.connect(self._changeRenderingMode)

    def _changeRenderingMode(self, index):
        self.renderingModeChanged.emit(RenderingMode(index))
