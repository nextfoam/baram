#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING

from dataclasses import dataclass
import asyncio
from pathlib import Path
from typing import Optional

import qasync

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QToolBar, QVBoxLayout, QWidgetAction
from PySide6.QtGui import QAction, QIcon, QPixmap

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer
from vtkmodules.vtkIOGeometry import vtkOpenFOAMReader
from vtkmodules.vtkFiltersGeometry import  vtkGeometryFilter
from vtkmodules.vtkCommonDataModel import vtkCompositeDataSet
# load implementations for rendering and interaction factory classes
import vtkmodules.vtkRenderingOpenGL2
import vtkmodules.vtkInteractionStyle

from coredb import coredb
from resources import resource
from openfoam.file_system import FileSystem
from .tabified_dock import TabifiedDock
if TYPE_CHECKING:
    from .main_window import MainWindow

import vtk


DISPLAY_MODE_POINTS         = 0
DISPLAY_MODE_WIREFRAME      = 1
DISPLAY_MODE_SURFACE        = 2
DISPLAY_MODE_SURFACE_EDGE   = 3
# DISPLAY_MODE_FEATURE        = 4

@dataclass
class ActorInfo:
    # It is not clear if the references of these two values should be kept
    #    dataset: vtk.vtkDataObject
    #    gFilter: vtk.vtkGeometryFilter
    mapper: vtkPolyDataMapper
    actor: vtkActor

    selected: bool

    show: bool
    viewMode: int
    outLine: bool

    position: list
    rotation: list
    color: list

    opacity: float

def getActorInfo(dataset) -> ActorInfo:
    gFilter = vtkGeometryFilter()
    gFilter.SetInputData(dataset)
    gFilter.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(gFilter.GetOutput())

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(255, 255, 255)

    selected = True

    show = True
    displayMode = DISPLAY_MODE_SURFACE_EDGE
    outLine = False

    position = [0.0, 0.0, 0.0]
    rotation = [0.0, 0.0, 0.0]
    color = [0.8, 0.8, 0.8]
    opacity = 1.0

    # return ActorInfo(dataset, gFilter, mapper, actor)
    actorInfo = ActorInfo(mapper, actor, selected, show, displayMode, outLine, position, rotation, color, opacity)
    return actorInfo


def build(mBlock):
    vtkMesh = {}
    n = mBlock.GetNumberOfBlocks()
    for i in range(0, n):
        if mBlock.HasMetaData(i):
            name = mBlock.GetMetaData(i).Get(vtkCompositeDataSet.NAME())
        else:
            name = ''
        ds = mBlock.GetBlock(i)
        dsType = ds.GetDataObjectType()
        if dsType == vtk.VTK_MULTIBLOCK_DATA_SET:
            vtkMesh[name] = build(ds)
        elif dsType == vtk.VTK_UNSTRUCTURED_GRID:
            if ds.GetNumberOfCells() > 0:
                vtkMesh[name] = getActorInfo(ds)
        elif dsType == vtk.VTK_POLY_DATA:
            vtkMesh[name] = getActorInfo(ds)
        else:
            vtkMesh[name] = f'Type {dsType}'  # ds

    return vtkMesh


"""
VtkMesh dict
{
    <region> : {
        "boundary" : {
            <boundary> : <ActorInfo>
            ...
        },
        "internalMesh" : <ActorInfo>,
        "zones" : {
            "cellZones" : {
                <cellZone> : <ActorInfo>,
                ...
            }
        }
    },
    ...
}
"""
def getVtkMesh(foamFilePath: Path, statusConfig: dict):
    r = vtkOpenFOAMReader()
    r.SetFileName(str(foamFilePath))
    r.DecomposePolyhedraOn()
    r.EnableAllCellArrays()
    r.EnableAllPointArrays()
    r.EnableAllPatchArrays()
    r.EnableAllLagrangianArrays()
    r.CreateCellToPointOn()
    r.CacheMeshOn()
    r.ReadZonesOn()

    for patchName, status in statusConfig.items():
        r.SetPatchArrayStatus(patchName, status)

    r.Update()

    vtkMesh = build(r.GetOutput())

    if 'boundary' in vtkMesh:  # single region mesh
        vtkMesh = {'': vtkMesh}

    return vtkMesh


class MeshDock(TabifiedDock):
    reloadMesh = Signal()
    meshLoaded = Signal()

    def __init__(self, parent: Optional['MainWindow'] = None):
        super().__init__(parent)

        self._main_window = parent

        self.setWindowTitle(self.tr("Mesh"))
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._widget = None
        self._renderer = None
        self._vtkMesh = None

        self._showAxes = True
        self._displayMode = DISPLAY_MODE_SURFACE_EDGE
        self._showCulling = False

        self.reloadMesh.connect(self.showOpenFoamMesh)

        self._main_window.windowClosed.connect(self._windowClosed)

    def vtkMesh(self):
        return self._vtkMesh

    def clear(self):
        if self._widget is not None:
            self._renderer.RemoveAllViewProps()
            self._widget.Render()

    def closeEvent(self, event):
        if self._widget is not None:
            self._widget.close()
            self._widget = None

    def _windowClosed(self, result):
        self.close()

    @qasync.asyncSlot()
    async def showOpenFoamMesh(self):
        self.clear()

        if self._widget is None:
            self._widget = QVTKRenderWindowInteractor(self)
            self._widget.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
            self._renderer = vtkRenderer()
            self._widget.GetRenderWindow().AddRenderer(self._renderer)

            self._widget.Initialize()
            self._widget.Start()

            self._addAxes()
            self._setBackGroundColor()

            self._graphicsPage = QVBoxLayout()
            self._graphicsPage.setSpacing(0)
            self._graphicsPage.setContentsMargins(9, 0, 9, 9)

            self._addToolBar()
            self._graphicsPage.addWidget(self._widget)
            frame = QFrame()
            frame.setLayout(self._graphicsPage)
            self.setWidget(frame)

        statusConfig = self.buildPatchArrayStatus()

        self._vtkMesh = await asyncio.to_thread(getVtkMesh, FileSystem.foamFilePath(), statusConfig)

        for region in self._vtkMesh:
            if 'boundary' not in self._vtkMesh[region]:  # polyMesh folder in multi-region constant folder
                continue

            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                self._renderer.AddActor(actorInfo.actor)

                actorInfo.actor.GetProperty().SetColor(actorInfo.color)
                actorInfo.actor.GetProperty().SetOpacity(actorInfo.opacity)
                actorInfo.actor.GetProperty().SetEdgeVisibility(True)
                actorInfo.actor.GetProperty().SetEdgeColor(0.1, 0.0, 0.3)
                actorInfo.actor.GetProperty().SetLineWidth(1.0)

        self._renderer.ResetCamera()
        self._widget.Render()

        self.meshLoaded.emit()

    def buildPatchArrayStatus(self):
        statusConfig = {'internalMesh': 0}

        db = coredb.CoreDB()
        regions = db.getRegions()

        if len(regions) == 1:  # single region
            for _, b, _ in db.getBoundaryConditions(regions[0]):
                statusConfig[f'patch/{b}'] = 1

            return statusConfig

        else:  # multi-region
            for r in regions:
                statusConfig[f'/{r}/internalMesh'] = 0
                for _, b, _ in db.getBoundaryConditions(r):
                    statusConfig[f'/{r}/patch/{b}'] = 1

            return statusConfig

    def _addAxes(self):
        self.actAxes = vtk.vtkAxesActor()

        self.actAxes.SetShaftTypeToCylinder()
        self.actAxes.SetCylinderResolution(4)
        self.actAxes.SetNormalizedShaftLength(0.9, 0.9, 0.9)
        self.actAxes.SetConeResolution(4)
        self.actAxes.SetNormalizedTipLength(0.3, 0.3, 0.3)

        actorAxesX = self.actAxes.GetXAxisCaptionActor2D()
        actorAxesY = self.actAxes.GetYAxisCaptionActor2D()
        actorAxesZ = self.actAxes.GetZAxisCaptionActor2D()

        actorTextAxesX = actorAxesX.GetTextActor()
        actorTextAxesY = actorAxesY.GetTextActor()
        actorTextAxesZ = actorAxesZ.GetTextActor()

        propAxesX = actorAxesX.GetCaptionTextProperty()
        propAxesY = actorAxesY.GetCaptionTextProperty()
        propAxesZ = actorAxesZ.GetCaptionTextProperty()

        actorTextAxesX.SetTextScaleModeToNone()
        actorTextAxesY.SetTextScaleModeToNone()
        actorTextAxesZ.SetTextScaleModeToNone()

        self.actAxes.SetXAxisLabelText('X')
        self.actAxes.SetYAxisLabelText('Y')
        self.actAxes.SetZAxisLabelText('Z')

        self.actAxes.SetNormalizedLabelPosition(1.2, 1.2, 1.2)

        propAxesX.SetFontSize(24)
        propAxesY.SetFontSize(24)
        propAxesZ.SetFontSize(24)

        propAxesX.SetColor(0.1, 0.1, 0.1)
        propAxesY.SetColor(0.1, 0.1, 0.1)
        propAxesZ.SetColor(0.1, 0.1, 0.1)

        self.axes = vtk.vtkOrientationMarkerWidget()
        self.axes.SetViewport(0.0, 0.0, 0.2, 0.2)
        self.axes.SetOrientationMarker(self.actAxes)
        self.axes.SetInteractor(self._widget)

        self.axes.EnabledOn()
        self.axes.InteractiveOn()

        self.actAxes.SetVisibility(True)

    def _setBackGroundColor(self):
        self._renderer.GradientBackgroundOn()
        self._renderer.SetBackground2(0.32, 0.34, 0.43)
        self._renderer.SetBackground(0.90, 0.91, 0.91)

    def _addToolBar(self):
        self._toolBar = QToolBar()
        self._graphicsPage.addWidget(self._toolBar)

        self._addIcons(resource.file('graphicsIcons'))

        self._actionAxesOnOff = QAction(self.iconAxesOn, 'Axes On/Off', self._main_window)
        self._actionAxesOnOff.setCheckable(True)
        self._actionAxesOnOff.setChecked(self._showAxes)
        self._toolBar.addAction(self._actionAxesOnOff)
        self._toolBar.addSeparator()

        self._actionFit = QAction(self._iconFit, 'Fit', self._main_window)
        self._toolBar.addAction(self._actionFit)
        self._toolBar.addSeparator()

        self._actionPlusX = QAction(self._iconPlusX, '+X', self._main_window)
        self._toolBar.addAction(self._actionPlusX)
        self._actionPlusY = QAction(self._iconPlusY, '+Y', self._main_window)
        self._toolBar.addAction(self._actionPlusY)
        self._actionPlusZ = QAction(self._iconPlusZ, '+Z', self._main_window)
        self._toolBar.addAction(self._actionPlusZ)
        self._toolBar.addSeparator()

        self._displayModeCombo = QComboBox()
        self._displayModeCombo.addItems(['Points', 'Wireframe', 'Surface', 'SurfaceEdge'])  # 'Feature'
        self._displayModeCombo.setCurrentIndex(DISPLAY_MODE_SURFACE_EDGE)
        self._displayModeCombo.currentIndexChanged.connect(self._clickedVDisplayModeCombo)
        self._actionShowMode = QWidgetAction(self._main_window)
        self._actionShowMode.setDefaultWidget(self._displayModeCombo)
        self._toolBar.addAction(self._actionShowMode)
        self._toolBar.addSeparator()

        self._actionCulling = QAction(self._iconCullingOff, 'Surface Culling', self._main_window)
        self._actionCulling.setCheckable(True)
        self._toolBar.addAction(self._actionCulling)
        self._toolBar.addSeparator()

        self._toolBar.actionTriggered[QAction].connect(self.clickedToolBar)

    def _addIcons(self, path):
        self.iconAxesOff = self._newIcon(str(path / 'axesOff.png'))
        self.iconAxesOn = self._newIcon(str(path / 'axesOn.png'))

        self._iconFit = self._newIcon(str(path / 'fit.png'))

        self._iconPlusX = self._newIcon(str(path / 'plusX.png'))
        self._iconPlusY = self._newIcon(str(path / 'plusY.png'))
        self._iconPlusZ = self._newIcon(str(path / 'plusZ.png'))

        self._iconCullingOn = self._newIcon(str(path / 'cullingOn.png'))
        self._iconCullingOff = self._newIcon(str(path / 'cullingOff.png'))

    def _newIcon(self, path):
        wgIcon = QIcon()
        wgIcon.addPixmap(QPixmap(path))
        return wgIcon

    def _clickedVDisplayModeCombo(self, widget):
        actors = []
        for region in self._vtkMesh:
            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                actors.append(actorInfo.actor)

        curIndex = self._displayModeCombo.currentIndex()
        if curIndex == DISPLAY_MODE_POINTS:
            for a in actors:
                a.GetProperty().SetPointSize(3)
                a.GetProperty().SetColor(0.1, 0.0, 0.3)
                a.GetProperty().SetRepresentationToPoints()

        elif curIndex == DISPLAY_MODE_WIREFRAME:
            for a in actors:
                a.GetProperty().SetColor(0.1, 0.0, 0.3)
                a.GetProperty().SetLineWidth(0.5)
                a.GetProperty().SetRepresentationToWireframe()

        elif curIndex == DISPLAY_MODE_SURFACE:
            for a in actors:
                a.GetProperty().SetColor(0.8, 0.8, 0.8)
                a.GetProperty().SetRepresentationToSurface()
                a.GetProperty().EdgeVisibilityOff()

        elif curIndex == DISPLAY_MODE_SURFACE_EDGE:
            for a in actors:
                a.GetProperty().SetColor(0.8, 0.8, 0.8)
                a.GetProperty().SetRepresentationToSurface()
                a.GetProperty().EdgeVisibilityOn()
                a.GetProperty().SetEdgeColor(0.1, 0.0, 0.3)
                a.GetProperty().SetLineWidth(1.0)

        # elif curIndex == DISPLAY_MODE_FEATURE:
        #     for a in actors:

        self._widget.Render()

    def clickedToolBar(self, action):
        if action == self._actionAxesOnOff:
            if self._showAxes:
                self._showAxesOff()
            else:
                self._showAxesOn()

        elif action == self._actionFit:
            self._renderer.ResetCamera()

        elif action == self._actionPlusX:
            ...
        elif action == self._actionPlusY:
            ...
        elif action == self._actionPlusZ:
            ...

        elif action == self._actionCulling:
            if self._showCulling:
                self._showCullingOff()
            else:
                self._showCullingOn()

        self._widget.Render()

    def _showAxesOn(self):
        self._showAxes = True
        self._actionAxesOnOff.setIcon(self.iconAxesOn)
        self.axes.EnabledOn()

    def _showAxesOff(self):
        self._showAxes = True
        self._actionAxesOnOff.setIcon(self.iconAxesOff)
        self.axes.EnabledOff()

    def _showCullingOn(self):
        self._showCulling = True
        self._actionCulling.setIcon(self._iconCullingOn)

        actors = []
        for region in self._vtkMesh:
            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                actors.append(actorInfo.actor)

        for a in actors:
            a.GetProperty().FrontfaceCullingOn()

    def _showCullingOff(self):
        self._showCulling = False
        self._actionCulling.setIcon(self._iconCullingOff)

        actors = []
        for region in self._vtkMesh:
            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                actors.append(actorInfo.actor)

        for a in actors:
            a.GetProperty().FrontfaceCullingOff()
