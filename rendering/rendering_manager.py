#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal

from enum import Enum, auto


class RenderingMode(Enum):
    SURFACE        = 0
    SURFACE_EDGE   = auto()
    FEATURE        = auto()


SURFACE_MODE = 0
FEATURE_MODE = 1


class RenderingManager(QObject):
    renderingModeChanged = Signal(int, int)

    def __init__(self):
        super().__init__()
        self._mode = RenderingMode.SURFACE.value

    def mode(self):
        return self._mode

    def setRenderingMode(self, mode):
        old = self._mode
        self._mode = mode
        self.renderingModeChanged.emit(old, mode)

    def actorMode(self):
        return FEATURE_MODE if self._mode == RenderingMode.FEATURE.value else SURFACE_MODE


rendering = RenderingManager()