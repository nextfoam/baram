#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from dataclasses import dataclass

from PySide6.QtGui import QColor
from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonDataModel import vtkDataObject, vtkPlane
from vtkmodules.vtkFiltersCore import vtkClipPolyData, vtkThreshold, vtkPassThrough, vtkCutter
from vtkmodules.vtkFiltersExtraction import vtkExtractPolyDataGeometry, vtkExtractGeometry
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkDataSetMapper, vtkActor, vtkMapper
from vtkmodules.vtkCommonColor import vtkNamedColors

from libbaram.mesh import Bounds
from libbaram.colormap import sequentialRedLut


class DisplayMode(Enum):
    WIREFRAME      = auto()  # noqa: E221
    SURFACE        = auto()  # noqa: E221
    SURFACE_EDGE   = auto()  # noqa: E221


class MeshQualityIndex(Enum):
    ASPECT_RATIO = 'cellAspectRatio'
    NON_ORTHO_ANGLE = 'nonOrthoAngle'
    SKEWNESS = 'skewness'
    VOLUME = 'cellVolume'

    @classmethod
    def values(cls):
        return [c.value for c in cls]


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

        self._cellFilter = vtkPassThrough()
        self._cellFilter.SetInputData(dataSet)
        self._cutFilters = [vtkPassThrough()]
        self._cutFilters[0].SetInputConnection(self._cellFilter.GetOutputPort())

        self._mqEnabled = False
        self._mqIndex = MeshQualityIndex.VOLUME
        self._mqMax = 0
        self._mqMin = 0
        self._mqHigh = 0
        self._mqLow = 0

        self._mapper: vtkMapper = self._initMapper()
        self._mapper.SetInputConnection(self._cutFilters[0].GetOutputPort())
        self._mapper.ScalarVisibilityOff()
        self._mapper.SetScalarModeToUseCellFieldData()
        self._mapper.SetColorModeToMapScalars()
        self._mapper.SetLookupTable(sequentialRedLut)

        self._actor = vtkActor()
        self._actor.SetMapper(self._mapper)
        self._actor.GetProperty().SetDiffuse(0.3)
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

        self._cellFilter.SetInputData(dataSet)

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

    def clip(self, planes):
        for i in reversed(range(1, len(self._cutFilters))):
            self._cutFilters[i].RemoveAllInputConnections(0)
            self._cutFilters.pop()

        inputFilter = self._cutFilters[0]
        if planes and self._properties.cutEnabled:
            for c in planes:
                f = self._clipFilter(c)
                f.SetInputConnection(inputFilter.GetOutputPort())
                self._cutFilters.append(f)
                inputFilter = f

        self._mapper.SetInputConnection(inputFilter.GetOutputPort())
        self._mapper.Update()

    def slice(self, plane):
        for i in reversed(range(1, len(self._cutFilters))):
            self._cutFilters[i].RemoveAllInputConnections(0)
            self._cutFilters.pop()

        inputFilter = self._cutFilters[0]
        if plane is not None and self._properties.cutEnabled:
            f = vtkCutter()
            f.SetCutFunction(plane)
            f.GenerateTrianglesOff()
            f.SetInputConnection(inputFilter.GetOutputPort())
            self._cutFilters.append(f)
            inputFilter = f

        self._mapper.SetInputConnection(inputFilter.GetOutputPort())
        self._mapper.Update()

    def getScalarRange(self, index: MeshQualityIndex) -> (float, float):
        return 0, 1

    def setScalar(self, index: MeshQualityIndex):
        pass

    def setScalarBand(self, low, high):
        pass

    def clearCellFilter(self):
        pass

    def applyCellFilter(self):
        pass

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

    def _clipFilter(self, cutter: vtkPlane):
        raise NotImplementedError


class MeshActor(ActorInfo):
    def __init__(self, dataSet, id_, name):
        super().__init__(dataSet, id_, name, ActorType.MESH)

    def _initMapper(self) -> vtkDataSetMapper:
        return vtkDataSetMapper()

    def _clipFilter(self, cutter: vtkPlane):
        f = vtkExtractGeometry()
        f.SetImplicitFunction(cutter)
        f.ExtractInsideOff()
        f.SetExtractBoundaryCells(True)
        return f

    def getNumberOfDisplayedCells(self) -> int:
        return self._cutFilters[-1].GetOutput().GetNumberOfCells()

    def getScalarRange(self, index: MeshQualityIndex) -> (float, float):
        # print(f'Name: {self.name()} Field: {index.value}')
        scalars = self._dataSet.GetCellData().GetScalars(index.value)
        if scalars is None:
            return 0, 1

        left, right = scalars.GetRange()
        return left, right

    def setScalar(self, index: MeshQualityIndex):
        self._mqIndex = index

    def setScalarBand(self, low, high):
        self._mqLow = low
        self._mqHigh = high

    def clearCellFilter(self):
        self._cellFilter = vtkPassThrough()

        self._cellFilter.SetInputData(self._dataSet)

        self._cutFilters[0].RemoveAllInputConnections(0)
        self._cutFilters[0].SetInputConnection(self._cellFilter.GetOutputPort())

        self._mapper.ScalarVisibilityOff()

        self._mapper.Update()

    def applyCellFilter(self):
        self._cellFilter = vtkThreshold()
        self._cellFilter.AllScalarsOff()
        self._cellFilter.SetThresholdFunction(vtkThreshold.THRESHOLD_BETWEEN)

        self._cellFilter.SetLowerThreshold(self._mqLow)
        self._cellFilter.SetUpperThreshold(self._mqHigh)
        self._cellFilter.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_CELLS, self._mqIndex.value)

        self._cellFilter.SetInputData(self._dataSet)

        self._cutFilters[0].RemoveAllInputConnections(0)
        self._cutFilters[0].SetInputConnection(self._cellFilter.GetOutputPort())

        self._mapper.ScalarVisibilityOn()
        self._mapper.SetScalarRange(self._mqLow, self._mqHigh)
        self._mapper.SelectColorArray(self._mqIndex.value)

        self._mapper.Update()


class BoundaryActor(ActorInfo):
    def __init__(self, dataSet, id_, name):
        super().__init__(dataSet, id_, name, ActorType.BOUNDARY)

    def _initMapper(self) -> vtkPolyDataMapper:
        return vtkPolyDataMapper()

    def _clipFilter(self, cutter: vtkPlane):
        f = vtkExtractPolyDataGeometry()
        f.SetImplicitFunction(cutter)
        f.ExtractInsideOff()
        f.SetExtractBoundaryCells(True)
        return f


class GeometryActor(ActorInfo):
    def __init__(self, dataSet, id_, name):
        super().__init__(dataSet, id_, name, ActorType.GEOMETRY)
        
        self.setOpacity(0.9)

    def _initMapper(self) -> vtkPolyDataMapper:
        return vtkPolyDataMapper()

    def _clipFilter(self, cutter: vtkPlane):
        f = vtkClipPolyData()
        f.SetClipFunction(cutter)
        f.InsideOutOff()
        return f