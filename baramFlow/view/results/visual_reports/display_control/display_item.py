#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from uuid import UUID

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QLabel, QWidget, QHBoxLayout
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkCommonDataModel import vtkUnstructuredGrid
from vtkmodules.vtkFiltersCore import vtkGlyph3D, vtkMaskPoints, vtkPassThrough
from vtkmodules.vtkFiltersFlowPaths import vtkStreamTracer
from vtkmodules.vtkFiltersModeling import vtkRibbonFilter
from vtkmodules.vtkFiltersSources import vtkArrowSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from baramFlow.coredb.post_field import Field
from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from baramFlow.openfoam.solver_field import getSolverFieldName

from libbaram.vtk_threads import holdRendering, resumeRendering, to_vtk_thread
from widgets.rendering.rendering_widget import RenderingWidget


class ColorMode(Enum):
    SOLID = auto()  # noqa: E221
    FIELD = auto()  # noqa: E221


class DisplayMode(Enum):
    WIREFRAME      = auto()  # noqa: E221
    SURFACE        = auto()  # noqa: E221
    SURFACE_EDGE   = auto()  # noqa: E221


@dataclass
class Properties:
    visibility: bool
    opacity: float
    color: QColor
    colorMode: ColorMode
    displayMode: DisplayMode
    showVectors: bool = None
    showStreamlines: bool = None

    highlighted: bool = False

    def merge(self, properties):
        self.visibility = properties.visibility if properties.visibility == self.visibility else None
        self.opacity = properties.opacity if properties.opacity == self.opacity else None
        self.color = properties.color if properties.color == self.color else None
        self.colorMode = properties.colorMode if properties.colorMode == self.colorMode else None
        self.displayMode = properties.displayMode if properties.displayMode == self.displayMode else None
        self.showVectors = properties.showVectors if properties.showVectors == self.showVectors else None
        self.showStreamlines = properties.showStreamlines if properties.showStreamlines == self.showStreamlines else None


class Column(IntEnum):
    NAME_COLUMN = 0
    TYPE_COLUMN = auto()
    COLOR_COLUMN = auto()
    # CUT_ICON_COLUMN = auto()
    # VISIBLE_ICON_COLUMN = auto()


class DisplayItem(QTreeWidgetItem):
    sourceChanged = Signal(UUID)
    nameChanged = Signal(str)

    def __init__(self, parent, did: UUID, reportingScaffold: ReportingScaffold, internalMesh: vtkUnstructuredGrid, field: Field, useNodeValues: bool, lookupTable: vtkLookupTable, view: RenderingWidget):
        super().__init__(parent)

        self._did = did
        self._reportingScaffold = reportingScaffold
        self._internalMesh = internalMesh
        self._field = field
        self._useNodeValues = useNodeValues
        self._lookupTable = lookupTable
        self._view = view

        self._scaffoldMapper: vtkPolyDataMapper = vtkPolyDataMapper()
        self._scaffoldMapper.SetInputData(self._reportingScaffold.dataSet)
        if reportingScaffold.solidColor:
            self._scaffoldMapper.ScalarVisibilityOff()
        else:
            self._scaffoldMapper.ScalarVisibilityOn()

        self._scaffoldMapper.SetColorModeToMapScalars()
        self._scaffoldMapper.UseLookupTableScalarRangeOn()
        self._scaffoldMapper.SetLookupTable(lookupTable)

        self._scaffoldActor: vtkActor = vtkActor()
        self._scaffoldActor.SetMapper(self._scaffoldMapper)
        self._scaffoldActor.GetProperty().SetDiffuse(0.3)
        self._scaffoldActor.GetProperty().SetOpacity(reportingScaffold.opacity)
        self._scaffoldActor.GetProperty().SetAmbient(0.3)
        self._scaffoldActor.SetObjectName(str(self._did))
        self._scaffoldActor.SetVisibility(reportingScaffold.visibility)
        self._scaffoldActor.GetProperty().SetColor(reportingScaffold.color.redF(),
                                                   reportingScaffold.color.greenF(),
                                                   reportingScaffold.color.blueF())

        self._vectorMask: vtkMaskPoints = None
        self._vectorArrow: vtkArrowSource = None
        self._vectorGlyph: vtkGlyph3D = None
        self._vectorMapper: vtkPolyDataMapper = None
        self._vectorActor: vtkActor = None

        self._streamMask: vtkMaskPoints = None
        self._streamMapper: vtkPolyDataMapper = None
        self._streamActor: vtkActor = None

        if reportingScaffold.solidColor:
            colorMode = ColorMode.SOLID
        else:
            colorMode = ColorMode.FIELD

        if reportingScaffold.edges and reportingScaffold.faces:
            displayMode = DisplayMode.SURFACE_EDGE
        elif reportingScaffold.faces:
            displayMode = DisplayMode.SURFACE
        elif reportingScaffold.edges:
            displayMode = DisplayMode.WIREFRAME
        else:
            raise AssertionError

        self._properties = Properties(reportingScaffold.visibility,
                                      reportingScaffold.opacity,
                                      reportingScaffold.color,
                                      colorMode,
                                      displayMode,
                                      reportingScaffold.showVectors,
                                      reportingScaffold.showStreamlines,
                                      highlighted=False)

        self._displayModeApplicator = {
            DisplayMode.WIREFRAME: self._applyWireframeMode,
            DisplayMode.SURFACE: self._applySurfaceMode,
            DisplayMode.SURFACE_EDGE: self._applySurfaceEdgeMode
        }

        self._colorWidget = QLabel()

        self.setText(Column.NAME_COLUMN, reportingScaffold.name)
        self.setText(Column.TYPE_COLUMN, reportingScaffold.name)

        self._updateColorColumn()

        self._displayModeApplicator[displayMode]()

        self._view.addActor(self._scaffoldActor)

        self._task = asyncio.create_task(self.updateScaffoldInfo())

        self._setField(field, useNodeValues)

    async def updateScaffoldInfo(self):
        self.setText(Column.NAME_COLUMN, self._reportingScaffold.name)

        self._scaffoldMapper.SetInputData(self._reportingScaffold.dataSet)
        holdRendering()
        await to_vtk_thread(self._scaffoldMapper.Update)
        resumeRendering()

        if self._properties.showVectors:
            await self._setUpVectors()

        if self._properties.showStreamlines:
            self._setUpStreamlines()

    def setField(self, field: Field, useNodeValues: bool):
        if field == self._field and useNodeValues == self._useNodeValues:
            print('same field configured')
            return

        self._field = field
        self._useNodeValues = useNodeValues

        self._setField(field, useNodeValues)

    def _setField(self, field: Field, useNodeValues: bool):
        if useNodeValues:
            self._scaffoldMapper.SetScalarModeToUsePointFieldData()
        else:
            self._scaffoldMapper.SetScalarModeToUseCellFieldData()

        solverFieldName = getSolverFieldName(field)
        self._scaffoldMapper.SelectColorArray(solverFieldName)

        self._scaffoldMapper.Update()

    def properties(self) -> Properties:
        return self._properties

    def actor(self) -> vtkActor:
        return self._scaffoldActor

    def did(self) -> UUID:
        return self._did

    def scaffold(self) -> ReportingScaffold:
        return self._reportingScaffold

    def dataSEt(self):
        return self._reportingScaffold.dataSet

    def isActorVisible(self) -> bool:
        return self._properties.visibility

    def colorMode(self) -> ColorMode:
        return self._properties.colorMode

    def setupColorWidget(self, treeWidget: QTreeWidget):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(9, 1, 9, 1)
        layout.addWidget(self._colorWidget)
        # self._colorWidget.setFrameShape(QFrame.Shape.Box)
        self._colorWidget.setMinimumSize(16, 16)
        treeWidget.setItemWidget(self, Column.COLOR_COLUMN, widget)

    def setActorVisible(self, visibility):
        self._properties.visibility = visibility
        self._reportingScaffold.visibility = visibility

        self._scaffoldActor.SetVisibility(visibility)

        self._updateColorColumn()

        self._reportingScaffold.markUpdated()

    def setDisplayMode(self, mode: DisplayMode):
        self._properties.displayMode = mode
        self._displayModeApplicator[mode]()

        if mode == DisplayMode.SURFACE_EDGE:
            self._reportingScaffold.edges = True
            self._reportingScaffold.faces = True
        elif mode == DisplayMode.SURFACE:
            self._reportingScaffold.edges = False
            self._reportingScaffold.faces = True
        elif mode == DisplayMode.WIREFRAME:
            self._reportingScaffold.edges = True
            self._reportingScaffold.faces = False
        else:
            raise AssertionError

        self._reportingScaffold.markUpdated()

    def setOpacity(self, opacity):
        self._properties.opacity = opacity
        self._reportingScaffold.opacity = opacity

        self._scaffoldActor.GetProperty().SetOpacity(opacity)
        if self._vectorActor is not None:
            self._vectorActor.GetProperty().SetOpacity(opacity)

        self._reportingScaffold.markUpdated()

    def setActorColor(self, color: QColor):
        self._properties.color = color
        self._reportingScaffold.color = color

        self._scaffoldActor.GetProperty().SetColor(color.redF(), color.greenF(), color.blueF())
        if self._vectorActor is not None:
            self._vectorActor.GetProperty().SetColor(color.redF(), color.greenF(), color.blueF())
        self._updateColorColumn()

        self._reportingScaffold.markUpdated()

    def setColorMode(self, mode: ColorMode):
        self._properties.colorMode = mode
        if mode == ColorMode.SOLID:
            self._scaffoldMapper.ScalarVisibilityOff()
            self._reportingScaffold.solidColor = False
            if self._vectorActor is not None:
                self._vectorMapper.ScalarVisibilityOff()
            self._reportingScaffold.solidColor = True
        elif mode == ColorMode.FIELD:
            self._scaffoldMapper.ScalarVisibilityOn()
            self._reportingScaffold.solidColor = False
            if self._vectorActor is not None:
                self._vectorMapper.ScalarVisibilityOn()
        else:
            raise AssertionError

        self._updateColorColumn()

        self._reportingScaffold.markUpdated()

    def setHighlighted(self, highlighted):
        if self._properties.highlighted != highlighted:
            self._properties.highlighted = highlighted
            if highlighted:
                self._highlightOn()
            else:
                self._highlightOff()

    def _highlightOn(self):
        self._applySurfaceEdgeMode()
        self._scaffoldActor.GetProperty().SetDiffuse(0.6)
        self._scaffoldActor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Magenta'))
        self._scaffoldActor.GetProperty().SetLineWidth(2)

    def _highlightOff(self):
        self._displayModeApplicator[self._properties.displayMode]()
        self._scaffoldActor.GetProperty().SetDiffuse(0.3)
        self._scaffoldActor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Gray'))
        self._scaffoldActor.GetProperty().SetLineWidth(1)

    def colorWidget(self):
        return self._colorWidget

    def _applyWireframeMode(self):
        if not self._properties.highlighted:
            self._scaffoldActor.GetProperty().SetRepresentationToWireframe()

    def _applySurfaceMode(self):
        if not self._properties.highlighted:
            self._scaffoldActor.GetProperty().SetRepresentationToSurface()
            self._scaffoldActor.GetProperty().EdgeVisibilityOff()

    def _applySurfaceEdgeMode(self):
        self._scaffoldActor.GetProperty().SetRepresentationToSurface()
        self._scaffoldActor.GetProperty().EdgeVisibilityOn()
        self._scaffoldActor.GetProperty().SetLineWidth(1.0)

    def _updateColorColumn(self):
        if self.isActorVisible():
            if self._properties.colorMode == ColorMode.SOLID:
                color = self._properties.color
                self._colorWidget.setStyleSheet(
                    f'background-color: rgb({color.red()}, {color.green()}, {color.blue()});'
                    'border: 1px solid LightGrey; border-radius: 3px;')
            elif self._properties.colorMode == ColorMode.FIELD:
                self._colorWidget.setStyleSheet(
                    'background-color: qlineargradient(x1: 0, y1: 0,x2: 1, y2: 1, stop: 0 #ff0000, stop: 0.33 #ffff00, stop: 0.66 #00c0ff, stop: 1 #c000ff);'
                    'border: 1px solid LightGrey; border-radius: 3px;')
            else:
                raise AssertionError
        else:
            self._colorWidget.setStyleSheet('')


    def close(self):
        self._view.removeActor(self._scaffoldActor)
        if self._vectorActor is not None:
            self._view.removeActor(self._vectorActor)

    async def showVectors(self):
        if self._vectorActor is None:
            await self._setUpVectors()

        self._properties.showVectors = True
        self._reportingScaffold.showVectors = True

        self._vectorActor.SetVisibility(True)

        self._reportingScaffold.markUpdated()

    def hideVectors(self):
        if self._vectorActor is None:
            return

        self._properties.showVectors = False
        self._reportingScaffold.showVectors = False

        self._vectorActor.SetVisibility(False)

        self._reportingScaffold.markUpdated()

    def _prepareVectorFilterPipeline(self):
        self._vectorMask = vtkMaskPoints()
        self._vectorMask.RandomModeOn()
        self._vectorMask.SetRandomModeType(vtkMaskPoints.RANDOM_SAMPLING)  # Configuration ???
        self._vectorMask.SetMaximumNumberOfPoints(100)  # Configuration

        self._vectorArrow = vtkArrowSource()
        self._vectorArrow.SetTipResolution(16)
        self._vectorArrow.SetTipLength(0.3)
        self._vectorArrow.SetTipRadius(0.1)

        self._vectorGlyph = vtkGlyph3D()
        self._vectorGlyph.SetVectorModeToUseVector()
        self._vectorGlyph.SetScaleFactor(1.0)
        self._vectorGlyph.SetColorModeToColorByScalar()
        self._vectorGlyph.SetScaleModeToScaleByVector()
        self._vectorGlyph.OrientOn()

        self._vectorGlyph.SetSourceConnection(self._vectorArrow.GetOutputPort())
        self._vectorGlyph.SetInputConnection(self._vectorMask.GetOutputPort())

        self._vectorMapper = vtkPolyDataMapper()
        self._vectorMapper.SetColorModeToMapScalars()
        self._vectorMapper.UseLookupTableScalarRangeOn()
        self._vectorMapper.SetLookupTable(self._lookupTable)

        self._vectorActor = vtkActor()
        self._vectorActor.SetMapper(self._vectorMapper)
        self._vectorActor.GetProperty().SetDiffuse(0.3)
        self._vectorActor.GetProperty().SetAmbient(0.3)
        self._vectorActor.SetObjectName(str(self._did))

        self._view.addActor(self._vectorActor)

    async def _setUpVectors(self):
        if self._vectorActor is None:
            self._prepareVectorFilterPipeline()

        self._vectorMask.SetInputData(self._reportingScaffold.dataSet)

        self._vectorGlyph.Update()

        self._vectorMapper.SetInputData(self._vectorGlyph.GetOutput())

        if self._properties.colorMode == ColorMode.FIELD:
            self._vectorMapper.ScalarVisibilityOn()
        else:
            self._vectorMapper.ScalarVisibilityOff()

        self._vectorActor.GetProperty().SetOpacity(self._properties.opacity)
        self._vectorActor.SetVisibility(self._properties.showVectors)

    def showStreamlines(self):
        if self._streamActor is None:
            self._setUpStreamlines()

        self._properties.showStreamlines = True
        self._reportingScaffold.showStreamlines = True

        self._streamActor.SetVisibility(True)

        self._reportingScaffold.markUpdated()

    def hideStreamlines(self):
        if self._streamActor is None:
            return

        self._properties.showStreamlines = False
        self._reportingScaffold.showStreamlines = False

        self._streamActor.SetVisibility(False)

        self._reportingScaffold.markUpdated()

    def _prepareStreamFilterPipeline(self):
        self._streamMask = vtkMaskPoints()
        self._streamMask.RandomModeOn()
        self._streamMask.SetRandomModeType(vtkMaskPoints.RANDOM_SAMPLING)  # Configuration ???
        self._streamMask.SetMaximumNumberOfPoints(100)  # Configuration

        self._streamTracer = vtkStreamTracer()
        self._streamTracer.SetComputeVorticity(True)

        self._streamTracer.SetIntegratorType(vtkStreamTracer.RUNGE_KUTTA45)  # Configuration

        self._streamTracer.SetInitialIntegrationStep(0.3)  # Configuration
        self._streamTracer.SetMinimumIntegrationStep(0.1)  # Configuration
        self._streamTracer.SetMaximumError(0.1)  # Configuration ???

        self._streamTracer.SetMaximumPropagation(3)  # Configuration

        self._integrateForward = True  # Configuration
        self._integrateBackward = False  # Configuration

        if self._integrateForward and self._integrateBackward:
            self._streamTracer.SetIntegrationDirectionToBoth()
        elif self._integrateForward:
            self._streamTracer.SetIntegrationDirectionToForward()
        elif self._integrateBackward:
            self._streamTracer.SetIntegrationDirectionToBackward()
        else:
            raise AssertionError

        self._streamTracer.SetSourceConnection(self._streamMask.GetOutputPort())

        self._lineType = 'ribbon'

        if self._lineType == 'ribbon':
            self._streamDeco = vtkRibbonFilter()
            self._streamDeco.SetInputConnection(self._streamTracer.GetOutputPort())
            self._streamDeco.SetWidth(0.01)  # Configuration
            self._streamDeco.SetAngle(0)
            self._streamDeco.VaryWidthOff()
        elif self._lineType == 'line':
            self._streamDeco = vtkPassThrough()
        else:
            raise AssertionError


        self._streamMapper = vtkPolyDataMapper()
        self._streamMapper.SetColorModeToMapScalars()
        self._streamMapper.UseLookupTableScalarRangeOn()
        self._streamMapper.SetLookupTable(self._lookupTable)

        self._streamActor = vtkActor()
        self._streamActor.SetMapper(self._streamMapper)
        self._streamActor.GetProperty().SetDiffuse(0.3)
        self._streamActor.GetProperty().SetAmbient(0.3)
        self._streamActor.SetObjectName(str(self._did))

        self._view.addActor(self._streamActor)

    def _setUpStreamlines(self):
        if self._streamActor is None:
            self._prepareStreamFilterPipeline()

        self._streamMask.SetInputData(self._reportingScaffold.dataSet)

        self._streamTracer.SetInputData(self._internalMesh)

        self._streamDeco.Update()

        self._streamMapper.SetInputData(self._streamDeco.GetOutput())

        if self._properties.colorMode == ColorMode.FIELD:
            self._streamMapper.ScalarVisibilityOn()
        else:
            self._streamMapper.ScalarVisibilityOff()

        self._streamActor.GetProperty().SetOpacity(self._properties.opacity)
        self._streamActor.SetVisibility(self._properties.showStreamlines)

