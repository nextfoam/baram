#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from dataclasses import dataclass

from PySide6.QtGui import QColor
from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonCore import VTK_UNSTRUCTURED_GRID
from vtkmodules.vtkFiltersCore import vtkClipPolyData
from vtkmodules.vtkFiltersExtraction import vtkExtractPolyDataGeometry, vtkExtractGeometry
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkDataSetMapper, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors

from libbaram.mesh import Bounds


class DisplayMode(Enum):
    WIREFRAME      = auto()
    SURFACE        = auto()
    SURFACE_EDGE   = auto()


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


class ActorSource:
    def __new__(cls, *args, **kwargs):
        if cls is ActorSource:
            raise TypeError(f"only children of '{cls.__name__}' may be instantiated")
        return super().__new__(cls)

    def __init__(self, dataSet, mapper):
        self._dataSet = dataSet
        self._mapper = mapper

        self._mapper.SetInputData(self._dataSet)

    def mapper(self):
        return self._mapper

    def setDataSet(self, dataSet):
        self._dataSet = dataSet
        self._mapper.SetInputData(dataSet)
        self._mapper.Update()

    def dataSet(self):
        return self._dataSet

    def getBounds(self):
        return self._dataSet.GetBounds()

    def cut(self, cutters, clip):
        dataSet = self._dataSet
        for c in cutters:
            filter = self._newClipFilter(c) if clip else self._newExtractFilter(c)
            filter.SetInputData(dataSet)
            filter.Update()
            dataSet = filter.GetOutput()

        self._mapper.SetInputData(dataSet)
        self._mapper.Update()

    def clearFilter(self):
        self._mapper.SetInputData(self._dataSet)
        self._mapper.Update()

    def _newExtractFilter(self, cutter):
        raise NotImplementedError

    def _newClipFilter(self, cutter):
        raise NotImplementedError


class UnstructuredGrid(ActorSource):
    def __init__(self, unstructuredGrid):
        super().__init__(unstructuredGrid, vtkDataSetMapper())

    def _newExtractFilter(self, cutter):
        filter = vtkExtractGeometry()
        filter.SetImplicitFunction(cutter.plane)
        filter.SetExtractInside(cutter.invert)
        filter.SetExtractBoundaryCells(True)

        return filter

    def _newClipFilter(self, cutter):
        return self._newExtractFilter(cutter)


class PolyData(ActorSource):
    def __init__(self, polyData):
        super().__init__(polyData, vtkPolyDataMapper())

    def _newExtractFilter(self, cutter):
        filter = vtkExtractPolyDataGeometry()
        filter.SetImplicitFunction(cutter.plane)
        filter.SetExtractInside(cutter.invert)
        filter.SetExtractBoundaryCells(True)

        return filter

    def _newClipFilter(self, cutter):
        filter = vtkClipPolyData()
        filter.SetClipFunction(cutter.plane)
        filter.SetInsideOut(cutter.invert)

        return filter


class ActorInfo(QObject):
    sourceChanged = Signal(str)
    nameChanged = Signal(str)

    def __init__(self, dataSet, id_, name, type):
        super().__init__()

        self._id = id_
        self._name = name
        self._type = type
        self._source = None
        self._mapper = None
        self._actor = vtkActor()

        if dataSet.GetDataObjectType() == VTK_UNSTRUCTURED_GRID:
            self._source = UnstructuredGrid(dataSet)
        else:
            self._source = PolyData(dataSet)

        self._mapper = self._source.mapper()
        self._mapper.ScalarVisibilityOff()

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
        return self._source.dataSet()

    def actor(self):
        return self._actor

    def properties(self):
        return self._properties

    def bounds(self):
        return Bounds(*self._source.getBounds())

    def isVisible(self):
        return self._properties.visibility

    def color(self):
        return self._properties.color

    def isCutEnabled(self):
        return self._properties.cutEnabled

    def isHighlighted(self):
        return self._properties.highlighted

    def setDataSet(self, dataSet):
        self._source.setDataSet(dataSet)
        self.sourceChanged.emit(self._id)

    def setName(self, name):
        self._name = name
        self.nameChanged.emit(name)

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

    def setCutEnabled(self, enabled):
        self._properties.cutEnabled = enabled

    def setHighlighted(self, highlighted):
        if self._properties.highlighted != highlighted:
            self._properties.highlighted = highlighted
            self._applyHighlight()

    def copyProperties(self, actorInfo):
        self._properties = actorInfo.properties()
        self._applyVisibility()
        self._applyOpacity()
        self._applyColor()
        self._applyDisplayMode()
        self._applyHighlight()

    def cut(self, cutters):
        if cutters and self.isCutEnabled():
            self._source.cut(cutters, self._type == ActorType.GEOMETRY)
        else:
            self._source.clearFilter()

    def _applyVisibility(self):
        self._actor.SetVisibility(self._properties.visibility)

    def _applyOpacity(self):
        self._actor.GetProperty().SetOpacity(self._properties.opacity)

    def _applyColor(self):
        color = self._properties.color
        self._actor.GetProperty().SetColor(color.redF(), color.greenF(), color.blueF())

    def _applyDisplayMode(self):
        self._displayModeApplicator[self._properties.displayMode]()

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

    def _applyHighlight(self):
        if self._properties.highlighted:
            self._applySurfaceEdgeMode()
            self._actor.GetProperty().SetDiffuse(0.6)
            self._actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Magenta'))
            self._actor.GetProperty().SetLineWidth(2)
        else:
            self._applyDisplayMode()
            self._actor.GetProperty().SetDiffuse(0.3)
            self._actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Gray'))
            self._actor.GetProperty().SetLineWidth(1)
