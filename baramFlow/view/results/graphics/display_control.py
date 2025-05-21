#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from enum import Enum, IntEnum, auto
from uuid import UUID

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QLabel, QWidget, QHBoxLayout
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkCommonDataModel import vtkDataObject, vtkUnstructuredGrid
from vtkmodules.vtkFiltersCore import vtkGlyph3D, vtkMaskPoints, vtkPassThrough
from vtkmodules.vtkFiltersFlowPaths import vtkStreamTracer
from vtkmodules.vtkFiltersModeling import vtkRibbonFilter
from vtkmodules.vtkFiltersSources import vtkArrowSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from baramFlow.base.graphic.graphic import Graphic, StreamlineType
from baramFlow.base.field import Field
from baramFlow.base.graphic.display_item import DisplayItem
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB
from baramFlow.openfoam.solver_field import getSolverFieldName

from libbaram.vtk_threads import vtk_run_in_thread
from widgets.rendering.rendering_widget import RenderingWidget


class ColorMode(Enum):
    SOLID = auto()  # noqa: E221
    FIELD = auto()  # noqa: E221


class DisplayMode(Enum):
    WIREFRAME      = auto()  # noqa: E221
    SURFACE        = auto()  # noqa: E221
    SURFACE_EDGE   = auto()  # noqa: E221


class Glyph3DArray(IntEnum):
    SCALARS = 0
    VECTORS = 1
    NORMALS = 2
    COLOR_SCALARS = 3


class Column(IntEnum):
    NAME_COLUMN = 0
    TYPE_COLUMN = auto()
    COLOR_COLUMN = auto()
    # CUT_ICON_COLUMN = auto()
    # VISIBLE_ICON_COLUMN = auto()


class DisplayControl(QTreeWidgetItem):
    def __init__(self, parent, did: UUID, graphic: Graphic, displayItem: DisplayItem, internalMesh: vtkUnstructuredGrid, field: Field, useNodeValues: bool, lookupTable: vtkLookupTable, view: RenderingWidget):
        super().__init__(parent)

        self._did = did
        self._graphic = graphic
        self._displayItem = displayItem
        self._internalMesh = internalMesh
        self._field = field
        self._useNodeValues = useNodeValues
        self._lookupTable = lookupTable
        self._view = view

        self._scaffoldMapper: vtkPolyDataMapper = vtkPolyDataMapper()
        self._scaffoldMapper.SetInputData(self._displayItem.dataSet)
        if displayItem.solidColor:
            self._scaffoldMapper.ScalarVisibilityOff()
        else:
            self._scaffoldMapper.ScalarVisibilityOn()

        self._scaffoldMapper.SetColorModeToMapScalars()
        self._scaffoldMapper.UseLookupTableScalarRangeOn()
        self._scaffoldMapper.InterpolateScalarsBeforeMappingOn()
        self._scaffoldMapper.SetLookupTable(lookupTable)

        self._scaffoldActor: vtkActor = vtkActor()
        self._scaffoldActor.SetMapper(self._scaffoldMapper)
        self._scaffoldActor.GetProperty().SetDiffuse(0.3)
        self._scaffoldActor.GetProperty().SetOpacity(displayItem.opacity)
        self._scaffoldActor.GetProperty().SetAmbient(0.3)
        self._scaffoldActor.SetObjectName(str(self._did))
        self._scaffoldActor.SetVisibility(displayItem.visibility)
        self._scaffoldActor.GetProperty().SetColor(displayItem.color.redF(),
                                                   displayItem.color.greenF(),
                                                   displayItem.color.blueF())
        self._scaffoldActor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Gray'))
        self._scaffoldActor.GetProperty().SetLineWidth(1.0)
        if displayItem.frontFaceCulling:
            self._scaffoldActor.GetProperty().FrontfaceCullingOn()

        self._vectorMask: vtkMaskPoints = None
        self._vectorArrow: vtkArrowSource = None
        self._vectorGlyph: vtkGlyph3D = None
        self._vectorMapper: vtkPolyDataMapper = None
        self._vectorActor: vtkActor = None

        self._streamMask: vtkMaskPoints = None
        self._streamMapper: vtkPolyDataMapper = None
        self._streamActor: vtkActor = None

        self._highlighted = False

        self._colorWidget = QLabel()

        self.setText(Column.NAME_COLUMN, displayItem.name)
        typeString = ScaffoldsDB().scaffoldTypeString(displayItem.scaffoldUuid)
        self.setText(Column.TYPE_COLUMN, typeString)

        self._updateColorColumn()

        self._applyDisplayMode()

        self._view.addActor(self._scaffoldActor)

        self._task = asyncio.create_task(self.updateScaffoldInfo(), name=str(self._did))

    async def updateScaffoldInfo(self):
        self.setText(Column.NAME_COLUMN, self._displayItem.name)
        await self.executePipeline()

    # def setField(self, field: Field, useNodeValues: bool):
    #     if field == self._field and useNodeValues == self._useNodeValues:
    #         print('same field configured')
    #         return

    #     self._field = field
    #     self._useNodeValues = useNodeValues

    #     self._setField(field, useNodeValues)

    async def _setField(self, field: Field, useNodeValues: bool):
        if useNodeValues:
            self._scaffoldMapper.SetScalarModeToUsePointFieldData()
        else:
            self._scaffoldMapper.SetScalarModeToUseCellFieldData()

        solverFieldName = getSolverFieldName(field)
        self._scaffoldMapper.SelectColorArray(solverFieldName)

        await vtk_run_in_thread(self._scaffoldMapper.Update)

        if self._vectorActor is not None:
            self._vectorMapper.SelectColorArray(solverFieldName)
            await vtk_run_in_thread(self._vectorMapper.Update)

        if self._streamActor is not None:
            self._streamMapper.SelectColorArray(solverFieldName)
            await vtk_run_in_thread(self._streamMapper.Update)

    @property
    def opacity(self) -> float:
        return self._displayItem.opacity

    @property
    def color(self) -> QColor:
        return self._displayItem.color

    @property
    def visibility(self) -> bool:
        return self._displayItem.visibility

    def did(self) -> UUID:
        return self._did

    @property
    def displayItem(self) -> DisplayItem:
        return self._displayItem

    @property
    def colorMode(self) -> ColorMode:
        if self._displayItem.solidColor:
            return ColorMode.SOLID
        else:
            return ColorMode.FIELD

    @property
    def displayMode(self) -> DisplayMode:
        if self._displayItem.edges and self._displayItem.faces:
            return DisplayMode.SURFACE_EDGE
        elif self._displayItem.faces:
            return DisplayMode.SURFACE
        elif self._displayItem.edges:
            return DisplayMode.WIREFRAME
        else:
            raise AssertionError

    @property
    def frontFaceCulling(self) -> bool:
        return self._displayItem.frontFaceCulling

    @property
    def vectorsOn(self) -> bool:
        return self._displayItem.vectorsOn

    @property
    def streamlinesOn(self) -> bool:
        return self._displayItem.streamlinesOn

    def setupColorWidget(self, treeWidget: QTreeWidget):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(9, 1, 9, 1)
        layout.addWidget(self._colorWidget)
        # self._colorWidget.setFrameShape(QFrame.Shape.Box)
        self._colorWidget.setMinimumSize(16, 16)
        treeWidget.setItemWidget(self, Column.COLOR_COLUMN, widget)

    async def setActorVisible(self, visibility):
        self._displayItem.visibility = visibility

        self._scaffoldActor.SetVisibility(visibility)

        self._updateColorColumn()

        await self._displayItem.markUpdated()

    async def setDisplayMode(self, mode: DisplayMode):
        if mode == DisplayMode.SURFACE_EDGE:
            self._displayItem.edges = True
            self._displayItem.faces = True
        elif mode == DisplayMode.SURFACE:
            self._displayItem.edges = False
            self._displayItem.faces = True
        elif mode == DisplayMode.WIREFRAME:
            self._displayItem.edges = True
            self._displayItem.faces = False
        else:
            raise AssertionError

        await self._displayItem.markUpdated()

        if not self._highlighted:
            self._applyDisplayMode()

    def _applyDisplayMode(self):
        if self._displayItem.edges:
            self._scaffoldActor.GetProperty().EdgeVisibilityOn()
        else:
            self._scaffoldActor.GetProperty().EdgeVisibilityOff()

        if self._displayItem.faces:
            self._scaffoldActor.GetProperty().SetRepresentationToSurface()
        else:
            self._scaffoldActor.GetProperty().SetRepresentationToWireframe()

    async def cullFrontFace(self):
        self._displayItem.frontFaceCulling = True
        self._scaffoldActor.GetProperty().FrontfaceCullingOn()
        await self._displayItem.markUpdated()

    async def revealFrontFace(self):
        self._displayItem.frontFaceCulling = False
        self._scaffoldActor.GetProperty().FrontfaceCullingOff()
        await self._displayItem.markUpdated()

    async def setOpacity(self, opacity):
        self._displayItem.opacity = opacity

        self._scaffoldActor.GetProperty().SetOpacity(opacity)

        if self._vectorActor is not None:
            self._vectorActor.GetProperty().SetOpacity(opacity)

        if self._streamActor is not None:
            self._streamActor.GetProperty().SetOpacity(opacity)

        await self._displayItem.markUpdated()

    async def setActorColor(self, color: QColor):
        self._displayItem.color = color

        self._scaffoldActor.GetProperty().SetColor(color.redF(), color.greenF(), color.blueF())

        if self._vectorActor is not None:
            self._vectorActor.GetProperty().SetColor(color.redF(), color.greenF(), color.blueF())

        if self._streamActor is not None:
            self._streamActor.GetProperty().SetCoatColor(color.redF(), color.greenF(), color.blueF())

        self._updateColorColumn()

        await self._displayItem.markUpdated()

    async def setColorMode(self, mode: ColorMode):
        if mode == ColorMode.SOLID:
            self._displayItem.solidColor = True
            self._scaffoldMapper.ScalarVisibilityOff()
            if self._vectorActor is not None:
                self._vectorMapper.ScalarVisibilityOff()
            if self._streamMapper is not None:
                self._streamMapper.ScalarVisibilityOff()
        elif mode == ColorMode.FIELD:
            self._displayItem.solidColor = False
            self._scaffoldMapper.ScalarVisibilityOn()
            if self._vectorActor is not None:
                self._vectorMapper.ScalarVisibilityOn()
            if self._streamMapper is not None:
                self._streamMapper.ScalarVisibilityOn()
        else:
            raise AssertionError

        self._updateColorColumn()

        await self._displayItem.markUpdated()

    def setHighlighted(self, highlighted):
        if self._highlighted != highlighted:
            self._highlighted = highlighted
            if highlighted:
                self._highlightOn()
            else:
                self._highlightOff()

    def _highlightOn(self):
        self._scaffoldActor.GetProperty().SetRepresentationToSurface()
        self._scaffoldActor.GetProperty().EdgeVisibilityOn()
        self._scaffoldActor.GetProperty().SetDiffuse(0.6)
        self._scaffoldActor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Magenta'))
        self._scaffoldActor.GetProperty().SetLineWidth(2)

    def _highlightOff(self):
        self._applyDisplayMode()
        self._scaffoldActor.GetProperty().SetDiffuse(0.3)
        self._scaffoldActor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Gray'))
        self._scaffoldActor.GetProperty().SetLineWidth(1)

    def _updateColorColumn(self):
        if self._displayItem.visibility or self._displayItem.vectorsOn or self._displayItem.streamlinesOn:
            if self._displayItem.solidColor:
                color = self._displayItem.color
                self._colorWidget.setStyleSheet(
                    f'background-color: rgb({color.red()}, {color.green()}, {color.blue()});'
                    'border: 1px solid LightGrey; border-radius: 3px;')
            else:
                self._colorWidget.setStyleSheet(
                    'background-color: qlineargradient(x1: 0, y1: 0,x2: 1, y2: 1, stop: 0 #ff0000, stop: 0.33 #ffff00, stop: 0.66 #00c0ff, stop: 1 #c000ff);'
                    'border: 1px solid LightGrey; border-radius: 3px;')
        else:
            self._colorWidget.setStyleSheet('')


    def close(self):
        self._view.removeActor(self._scaffoldActor)

        if self._vectorActor is not None:
            self._view.removeActor(self._vectorActor)

        if self._streamActor is not None:
            self._view.removeActor(self._streamActor)

    async def showVectors(self):
        if self._vectorActor is None:
            await self._setUpVectors()

        self._displayItem.vectorsOn = True

        self._vectorActor.SetVisibility(True)

        await self._displayItem.markUpdated()

        self._updateColorColumn()

    async def hideVectors(self):
        if self._vectorActor is None:
            return

        self._displayItem.vectorsOn = False

        self._vectorActor.SetVisibility(False)

        await self._displayItem.markUpdated()

        self._updateColorColumn()

    def _prepareVectorFilterPipeline(self):
        self._vectorMask = vtkMaskPoints()
        self._vectorMask.SetOnRatio(1)
        self._vectorMask.RandomModeOn()
        self._vectorMask.SetRandomModeType(vtkMaskPoints.SPATIALLY_STRATIFIED)

        self._vectorArrow = vtkArrowSource()
        self._vectorArrow.SetTipResolution(16)
        self._vectorArrow.SetTipLength(0.3)
        self._vectorArrow.SetTipRadius(0.1)

        self._vectorGlyph = vtkGlyph3D()
        self._vectorGlyph.SetVectorModeToUseVector()

        self._vectorGlyph.SetColorModeToColorByScalar()
        self._vectorGlyph.OrientOn()

        self._vectorGlyph.SetSourceConnection(self._vectorArrow.GetOutputPort())
        self._vectorGlyph.SetInputConnection(self._vectorMask.GetOutputPort())

        self._vectorMapper = vtkPolyDataMapper()
        self._vectorMapper.SetColorModeToMapScalars()
        self._vectorMapper.UseLookupTableScalarRangeOn()
        self._vectorMapper.SetLookupTable(self._lookupTable)
        self._vectorMapper.SetScalarModeToUsePointFieldData()

        self._vectorActor = vtkActor()
        self._vectorActor.SetMapper(self._vectorMapper)
        self._vectorActor.GetProperty().SetDiffuse(0.3)
        self._vectorActor.GetProperty().SetAmbient(0.3)
        self._vectorActor.SetObjectName(str(self._did))

        self._view.addActor(self._vectorActor)

    async def _setUpVectors(self):
        if self._vectorActor is None:
            self._prepareVectorFilterPipeline()

        self._vectorMask.SetInputData(self._displayItem.dataSet)
        self._vectorMask.SetMaximumNumberOfPoints(self._displayItem.maxNumberOfSamplePoints)

        self._vectorGlyph.SetScaleFactor(float(self._graphic.vectorScaleFactor))

        vectorField = getSolverFieldName(self._graphic.vectorField)
        self._vectorGlyph.SetInputArrayToProcess(Glyph3DArray.VECTORS.value, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, vectorField)

        colorField = getSolverFieldName(self._graphic.field)
        self._vectorGlyph.SetInputArrayToProcess(Glyph3DArray.COLOR_SCALARS.value, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, colorField)

        if self._graphic.vectorFixedLength:
            self._vectorGlyph.SetScaleModeToDataScalingOff()
        else:
            self._vectorGlyph.SetScaleModeToScaleByVector()

        await vtk_run_in_thread(self._vectorGlyph.Update)

        self._vectorMapper.SetInputData(self._vectorGlyph.GetOutput())

        if self._displayItem.solidColor:
            self._vectorMapper.ScalarVisibilityOff()
        else:
            self._vectorMapper.ScalarVisibilityOn()

        self._vectorMapper.SelectColorArray(colorField)

        await vtk_run_in_thread(self._vectorMapper.Update)

        self._vectorActor.GetProperty().SetOpacity(self._displayItem.opacity)
        self._vectorActor.SetVisibility(self._displayItem.vectorsOn)

    async def showStreamlines(self):
        if self._streamActor is None:
            await self._setUpStreamlines()

        self._displayItem.streamlinesOn = True

        self._streamActor.SetVisibility(True)

        await self._displayItem.markUpdated()

        self._updateColorColumn()

    async def hideStreamlines(self):
        if self._streamActor is None:
            return

        self._displayItem.streamlinesOn = False

        self._streamActor.SetVisibility(False)

        await self._displayItem.markUpdated()

        self._updateColorColumn()

    def _prepareStreamFilterPipeline(self):
        self._streamMask = vtkMaskPoints()
        self._streamMask.SetOnRatio(1)
        self._streamMask.RandomModeOn()
        self._streamMask.SetRandomModeType(vtkMaskPoints.SPATIALLY_STRATIFIED)

        self._streamTracer = vtkStreamTracer()
        self._streamTracer.SetComputeVorticity(True)
        self._streamTracer.SetIntegrationStepUnit(vtkStreamTracer.LENGTH_UNIT)
        self._streamTracer.SetSourceConnection(self._streamMask.GetOutputPort())

        self._streamMapper = vtkPolyDataMapper()
        self._streamMapper.SetColorModeToMapScalars()
        self._streamMapper.UseLookupTableScalarRangeOn()
        self._streamMapper.SetLookupTable(self._lookupTable)
        self._streamMapper.SetScalarModeToUsePointFieldData()

        self._streamActor = vtkActor()
        self._streamActor.SetMapper(self._streamMapper)
        self._streamActor.GetProperty().SetDiffuse(0.3)
        self._streamActor.GetProperty().SetAmbient(0.3)
        self._streamActor.SetObjectName(str(self._did))

        self._view.addActor(self._streamActor)

    async def _setUpStreamlines(self):
        if self._streamActor is None:
            self._prepareStreamFilterPipeline()

        self._streamMask.SetInputData(self._displayItem.dataSet)
        self._streamMask.SetMaximumNumberOfPoints(self._displayItem.maxNumberOfSamplePoints)

        if self._graphic.accuracyControl:
            self._streamTracer.SetIntegratorType(vtkStreamTracer.RUNGE_KUTTA45)
        else:
            self._streamTracer.SetIntegratorType(vtkStreamTracer.RUNGE_KUTTA4)

        self._streamTracer.SetInitialIntegrationStep(float(self._graphic.stepSize))
        self._streamTracer.SetMinimumIntegrationStep(min(float(self._graphic.stepSize) * 0.1, 0.01))
        self._streamTracer.SetMaximumIntegrationStep(max(float(self._graphic.stepSize) * 10, 1.0))
        self._streamTracer.SetMaximumError(float(self._graphic.tolerance))

        self._streamTracer.SetMaximumPropagation(float(self._graphic.maxLength))

        if self._displayItem.streamlinesIntegrateForward and self._displayItem.streamlinesIntegrateBackward:
            self._streamTracer.SetIntegrationDirectionToBoth()
        elif self._displayItem.streamlinesIntegrateForward:
            self._streamTracer.SetIntegrationDirectionToForward()
        elif self._displayItem.streamlinesIntegrateBackward:
            self._streamTracer.SetIntegrationDirectionToBackward()
        else:
            raise AssertionError

        self._streamTracer.SetInputData(self._internalMesh)

        if self._graphic.streamlineType == StreamlineType.RIBBON:
            self._streamDeco = vtkRibbonFilter()
            self._streamDeco.SetInputConnection(self._streamTracer.GetOutputPort())
            self._streamDeco.SetWidth(float(self._graphic.lineWidth) / 2)
            self._streamDeco.SetAngle(0)
            self._streamDeco.VaryWidthOff()
        elif self._graphic.streamlineType == StreamlineType.LINE:
            self._streamDeco = vtkPassThrough()
            self._streamDeco.SetInputConnection(self._streamTracer.GetOutputPort())
            self._streamActor.GetProperty().SetLineWidth(float(self._graphic.lineWidth))
        else:
            raise AssertionError

        await vtk_run_in_thread(self._streamDeco.Update)

        self._streamMapper.SetInputData(self._streamDeco.GetOutput())

        if self._displayItem.solidColor:
            self._streamMapper.ScalarVisibilityOff()
        else:
            self._streamMapper.ScalarVisibilityOn()

        solverFieldName = getSolverFieldName(self._graphic.field)
        self._streamMapper.SelectColorArray(solverFieldName)

        await vtk_run_in_thread(self._streamMapper.Update)

        self._streamActor.GetProperty().SetOpacity(self._displayItem.opacity)
        self._streamActor.SetVisibility(self._displayItem.streamlinesOn)

    async def executePipeline(self):
        self._scaffoldMapper.SetInputData(self._displayItem.dataSet)

        await vtk_run_in_thread(self._scaffoldMapper.Update)

        if self._displayItem.vectorsOn or self._vectorActor is not None:
            await self._setUpVectors()

        if self._displayItem.streamlinesOn or self._streamActor is not None:
            await self._setUpStreamlines()

        await self._setField(self._graphic.field, self._graphic.useNodeValues)

