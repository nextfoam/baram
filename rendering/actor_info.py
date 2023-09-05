#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum ,auto

from PySide6.QtGui import QColor

from dataclasses import dataclass

from rendering.vtk_loader import polyDataToActor


class DisplayMode(Enum):
    WIREFRAME      = auto()
    SURFACE        = auto()
    SURFACE_EDGE   = auto()


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

    def size(self):
        return self.xMax - self.xMin, self.yMax - self.yMin, self.zMax - self.zMin


class ActorType(Enum):
    GEOMETRY = auto()
    BOUNDARY = auto()


class ActorInfo:
    @dataclass
    class Properties:
        visibility: bool
        opacity: float
        color: QColor
        displayMode: DisplayMode
        cutEnabled: bool
        highlighted: bool

        def merge(self, properties):
            self.visibility = properties.visibility if properties.visibility == self.visibility else None
            self.opacity = properties.opacity if properties.opacity == self.opacity else None
            self.color = properties.color if properties.color == self.color else None
            self.displayMode = properties.displayMode if properties.displayMode == self.displayMode else None
            self.cutEnabled = properties.cutEnabled if properties.cutEnabled == self.cutEnabled else None

    def __init__(self, polyData, id_, name, type):
        self._id = id_
        self._name = name
        self._type = type
        self._polyData = polyData

        self._actor = polyDataToActor(polyData)
        self._actor.SetObjectName(self._id)
        self._properties = None

        self._actor.GetProperty().SetOpacity(0.9)

        prop = self._actor.GetProperty()
        self._properties = self.Properties(self._actor.GetVisibility(),
                                           prop.GetOpacity(),
                                           QColor.fromRgbF(*prop.GetColor()),
                                           DisplayMode.SURFACE,
                                           True, False)

        self._displayModeApplicator = {
            DisplayMode.WIREFRAME: self._applyWireframeMode,
            DisplayMode.SURFACE: self._applySurfaceMode,
            DisplayMode.SURFACE_EDGE: self._applySurfaceEdgeMode
        }

    def id(self):
        return self._id

    def name(self):
        return self._name

    def type(self):
        return self._type

    def polyData(self):
        return self._polyData

    def actor(self):
        return self._actor

    def properties(self):
        return self._properties

    def bounds(self):
        return Bounds(*self._actor.GetBounds())

    def setName(self, name):
        self._name = name

    def isVisible(self):
        return self._properties.visibility

    def color(self):
        return self._properties.color

    def isCutEnabled(self):
        return self._properties.cutEnabled

    def isHighlighted(self):
        return self._properties.highlighted

    def setVisible(self, visibility):
        self._properties.visibility = visibility
        self._applyVisibility()

    def setOpacity(self, opacity):
        self._properties.opacity = opacity
        self._applyOpacity()

    def setColor(self, color: QColor):
        self._properties.color = color
        self._applyColor()

    def setDisplayMode(self, mode):
        self._properties.displayMode = mode
        self._applyDisplayMode()

    def setCutEnabled(self, cut):
        self._properties.cut = cut
        self._applyCut()

    def setHighlighted(self, highlighted):
        if self._properties.highlighted != highlighted:
            self._properties.highlighted = highlighted
            self._applyHighlight()

    def setProperties(self, properties):
        self._properties = properties
        self._applyVisibility()
        self._applyOpacity()
        self._applyColor()
        self._applyDisplayMode()
        self._applyCut()
        self._applyHighlight()

    def _applyVisibility(self):
        self._actor.SetVisibility(self._properties.visibility)

    def _applyOpacity(self):
        self._actor.GetProperty().SetOpacity(self._properties.opacity)

    def _applyColor(self):
        color = self._properties.color
        self._actor.GetProperty().SetColor(color.redF(), color.greenF(), color.blueF())

    def _applyDisplayMode(self):
        self._displayModeApplicator[self._properties.displayMode]()

    def _applyCut(self):
        return

    def _applyWireframeMode(self):
        self._actor.GetProperty().SetRepresentationToWireframe()

    def _applySurfaceMode(self):
        self._actor.GetProperty().SetRepresentationToSurface()
        self._actor.GetProperty().EdgeVisibilityOff()

    def _applySurfaceEdgeMode(self):
        self._actor.GetProperty().SetRepresentationToSurface()
        self._actor.GetProperty().EdgeVisibilityOn()
        self._actor.GetProperty().SetLineWidth(1.0)

    def _applyHighlight(self):
        # print(self._actor.GetProperty().GetDiffuse())
        # print(self._actor.GetProperty().GetSpecular())
        # print(self._actor.GetProperty().GetSpecularColor())
        # print(self._actor.GetProperty().GetSpecularPower())
        # print(self._actor.GetProperty().GetAmbient())
        if self._properties.highlighted:
            self._actor.GetProperty().SetDiffuse(0.6)
        else:
            self._actor.GetProperty().SetDiffuse(0.3)
