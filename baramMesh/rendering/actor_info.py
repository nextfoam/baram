#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from dataclasses import dataclass

from PySide6.QtGui import QColor
from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkFiltersCore import vtkClipPolyData
from vtkmodules.vtkFiltersExtraction import vtkExtractPolyDataGeometry, vtkExtractGeometry
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkDataSetMapper, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors

from libbaram.mesh import Bounds


class DisplayMode(Enum):
    WIREFRAME      = auto()  # noqa: E221
    SURFACE        = auto()  # noqa: E221
    SURFACE_EDGE   = auto()  # noqa: E221


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


class ActorType(Enum):
    GEOMETRY = auto()
    BOUNDARY = auto()
    MESH = auto()


class ActorInfo(QObject):
    sourceChanged = Signal(str)
    nameChanged = Signal(str)

    def __init__(self, dataSet, id_, name, type_):
        super().__init__()

        self._dataSet = dataSet
        self._id = id_
        self._name = name
        self._type = type_

        self._mapper = self._initMapper()
        self._mapper.SetInputData(self._dataSet)
        self._mapper.ScalarVisibilityOff()

        self._actor = vtkActor()
        self._actor.SetMapper(self._mapper)
        self._actor.GetProperty().SetDiffuse(0.3)
        self._actor.GetProperty().SetOpacity(0.9)
        self._actor.GetProperty().SetAmbient(0.3)
        self._actor.SetObjectName(self._id)

        prop = self._actor.GetProperty()
        self._properties = Properties(bool(self._actor.GetVisibility()),
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

    def dataSet(self):
        return self._dataSet

    def actor(self):
        return self._actor

    def properties(self):
        return self._properties

    def bounds(self):
        return Bounds(*self._dataSet.GetBounds())

    def isVisible(self):
        return self._properties.visibility

    def color(self):
        return self._properties.color

    def setDataSet(self, dataSet):
        self._dataSet = dataSet

        self._mapper.SetInputData(dataSet)
        self._mapper.Update()

        self.sourceChanged.emit(self._id)

    def setName(self, name):
        self._name = name
        self.nameChanged.emit(name)

    def setVisible(self, visibility):
        self._properties.visibility = visibility
        self._actor.SetVisibility(visibility)

    def setOpacity(self, opacity):
        self._properties.opacity = opacity
        self._actor.GetProperty().SetOpacity(opacity)

    def setColor(self, color: QColor):
        self._properties.color = color
        self._actor.GetProperty().SetColor(color.redF(), color.greenF(), color.blueF())

    def setDisplayMode(self, mode):
        self._properties.displayMode = mode
        self._displayModeApplicator[mode]()

    def setCutEnabled(self, enabled):
        self._properties.cutEnabled = enabled

    def setHighlighted(self, highlighted):
        if self._properties.highlighted != highlighted:
            self._properties.highlighted = highlighted
            if highlighted:
                self._highlightOn()
            else:
                self._highlightOff()

    def cut(self, cutters):
        if cutters and self._properties.cutEnabled:
            if self._type == ActorType.GEOMETRY:
                clip = True
            else:
                clip = False

            dataSet = self._dataSet
            for c in cutters:
                f = self._clipFilter(c) if clip else self._extractFilter(c)
                f.SetInputData(dataSet)
                f.Update()
                dataSet = f.GetOutput()

            self._mapper.SetInputData(dataSet)
            self._mapper.Update()
        else:
            self._mapper.SetInputData(self._dataSet)
            self._mapper.Update()

    def _applyWireframeMode(self):
        if not self._properties.highlighted:
            self._actor.GetProperty().SetRepresentationToWireframe()

    def _applySurfaceMode(self):
        if not self._properties.highlighted:
            self._actor.GetProperty().SetRepresentationToSurface()
            self._actor.GetProperty().EdgeVisibilityOff()

    def _applySurfaceEdgeMode(self):
        self._actor.GetProperty().SetRepresentationToSurface()
        self._actor.GetProperty().EdgeVisibilityOn()
        self._actor.GetProperty().SetLineWidth(1.0)

    def _highlightOn(self):
        self._applySurfaceEdgeMode()
        self._actor.GetProperty().SetDiffuse(0.6)
        self._actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Magenta'))
        self._actor.GetProperty().SetLineWidth(2)

    def _highlightOff(self):
        self._displayModeApplicator[self._properties.displayMode]()
        self._actor.GetProperty().SetDiffuse(0.3)
        self._actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Gray'))
        self._actor.GetProperty().SetLineWidth(1)

    def _initMapper(self):
        raise NotImplementedError

    def _extractFilter(self, cutter):
        raise NotImplementedError

    def _clipFilter(self, cutter):
        raise NotImplementedError


class UnstructuredGridActor(ActorInfo):
    def _initMapper(self) -> vtkDataSetMapper:
        mapper = vtkDataSetMapper()
        mapper.SetScalarModeToUseCellData()
        mapper.SetColorModeToMapScalars()
        return mapper

    def _extractFilter(self, cutter):
        f = vtkExtractGeometry()
        f.SetImplicitFunction(cutter.plane)
        f.SetExtractInside(cutter.invert)
        f.SetExtractBoundaryCells(True)
        return f

    def _clipFilter(self, cutter):
        return self._extractFilter(cutter)


class PolyDataActor(ActorInfo):
    def _initMapper(self) -> vtkPolyDataMapper:
        return vtkPolyDataMapper()

    def _extractFilter(self, cutter):
        f = vtkExtractPolyDataGeometry()
        f.SetImplicitFunction(cutter.plane)
        f.SetExtractInside(cutter.invert)
        f.SetExtractBoundaryCells(True)
        return f

    def _clipFilter(self, cutter):
        f = vtkClipPolyData()
        f.SetClipFunction(cutter.plane)
        f.SetInsideOut(cutter.invert)
        return f
