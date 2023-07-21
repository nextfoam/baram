#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rendering.rendering_manager import SURFACE_MODE, FEATURE_MODE
from dataclasses import dataclass


@dataclass
class Bounds:
    xMin: float
    xMax: float
    yMin: float
    yMax: float
    zMin: float
    zMax: float

    def merge(self, bounds):
        self.xMin = min(self.xMin, bounds.xMin)
        self.xMax = max(self.xMax, bounds.xMax)
        self.yMin = min(self.yMin, bounds.yMin)
        self.yMax = max(self.yMax, bounds.yMax)
        self.zMin = min(self.zMin, bounds.zMin)
        self.zMax = max(self.zMax, bounds.zMax)


class ActorInfo:
    def __init__(self, surface, feature=None):
        self._actor = {
            SURFACE_MODE: surface,
            FEATURE_MODE: feature
        }

        self._name = None
        self._visible = True

    @property
    def surface(self):
        return self._actor[SURFACE_MODE]

    @property
    def feature(self):
        return self._actor[FEATURE_MODE]

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    def bounds(self):
        return Bounds(*self._actor[SURFACE_MODE].GetBounds())

    def actor(self, type_=SURFACE_MODE):
        return self._actor[type_]

    def isVisible(self):
        return self._visible

    def setVisible(self, visible):
        self._visible = visible
