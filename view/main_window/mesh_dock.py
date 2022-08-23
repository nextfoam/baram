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
from vtkmodules.vtkFiltersSources import vtkLineSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer, vtkCamera
from vtkmodules.vtkIOGeometry import vtkOpenFOAMReader
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
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

CAMERA_VIEW_PLUS_X  = 0
CAMERA_VIEW_MINUS_X = 1
CAMERA_VIEW_PLUS_Y  = 2
CAMERA_VIEW_MINUS_Y = 3
CAMERA_VIEW_PLUS_Z  = 4
CAMERA_VIEW_MINUS_Z = 5

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

    color: (int, int, int)
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

    color = [0.8, 0.8, 0.8]
    opacity = 1.0

    # return ActorInfo(dataset, gFilter, mapper, actor)
    actorInfo = ActorInfo(mapper, actor, selected, show, displayMode, outLine, color, opacity)
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

        self._axesOn = True
        self._originAxesOn = True

        self._orthogonalOn = True
        self._displayMode = DISPLAY_MODE_SURFACE_EDGE
        self._cullingOn = False

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

            self._graphicsPage = QVBoxLayout()
            self._graphicsPage.setSpacing(0)
            self._graphicsPage.setContentsMargins(6, 0, 6, 6)

            self._addToolBar()
            self._graphicsPage.addWidget(self._toolBar)
            self._graphicsPage.addWidget(self._widget)
            frame = QFrame()
            frame.setLayout(self._graphicsPage)
            self.setWidget(frame)

            self._addAxes()
            self._addOriginAxes()
            self._setBackGroundColor()

            self._addCamera()
            self._orthogonalMode()

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

        self._fitCamera()
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
        self._actAxes = vtk.vtkAxesActor()
        self._actAxes.SetVisibility(True)

        self._actAxes.SetShaftTypeToCylinder()
        self._actAxes.SetCylinderResolution(8)
        self._actAxes.SetNormalizedShaftLength(0.8, 0.8, 0.8)
        self._actAxes.SetConeResolution(8)
        self._actAxes.SetNormalizedTipLength(0.3, 0.3, 0.3)

        actorAxesX = self._actAxes.GetXAxisCaptionActor2D()
        actorAxesY = self._actAxes.GetYAxisCaptionActor2D()
        actorAxesZ = self._actAxes.GetZAxisCaptionActor2D()

        actorTextAxesX = actorAxesX.GetTextActor()
        actorTextAxesY = actorAxesY.GetTextActor()
        actorTextAxesZ = actorAxesZ.GetTextActor()

        propAxesX = actorAxesX.GetCaptionTextProperty()
        propAxesY = actorAxesY.GetCaptionTextProperty()
        propAxesZ = actorAxesZ.GetCaptionTextProperty()

        actorTextAxesX.SetTextScaleModeToNone()
        actorTextAxesY.SetTextScaleModeToNone()
        actorTextAxesZ.SetTextScaleModeToNone()

        self._actAxes.SetXAxisLabelText('X')
        self._actAxes.SetYAxisLabelText('Y')
        self._actAxes.SetZAxisLabelText('Z')

        self._actAxes.SetNormalizedLabelPosition(1.2, 1.2, 1.2)

        propAxesX.SetFontSize(20)
        propAxesY.SetFontSize(20)
        propAxesZ.SetFontSize(20)

        propAxesX.SetColor(0.9, 0.9, 0.9)
        propAxesY.SetColor(0.9, 0.9, 0.9)
        propAxesZ.SetColor(0.9, 0.9, 0.9)

        self._axes = vtk.vtkOrientationMarkerWidget()
        self._axes.SetViewport(0.0, 0.0, 0.2, 0.2)
        self._axes.SetOrientationMarker(self._actAxes)
        # self._axes.SetOutlineColor(1.0, 1.0, 1.0)
        self._axes.SetInteractor(self._widget)

        self._axes.EnabledOn()
        self._axes.InteractiveOn()

    def _addOriginAxes(self):
        self._originActorX = self._drawLine([[-10.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
        self._originActorY = self._drawLine([[0.0, -10.0, 0.0], [0.0, 10.0, 0.0]])
        self._originActorZ = self._drawLine([[0.0, 0.0, -10.0], [0.0, 0.0, 10.0]])

        self._renderer.AddActor(self._originActorX)
        self._renderer.AddActor(self._originActorY)
        self._renderer.AddActor(self._originActorZ)

    def _drawLine(self, points=[]):
        if len(points) < 2:
            points.append([-1.0, 0.0, 0.0])
            points.append([1.0, 0.0, 0.0])

        lineSource = vtkLineSource()
        lineSource.SetPoint1(points[0])
        lineSource.SetPoint2(points[1])

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(lineSource.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetLineWidth(1.0)
        actor.GetProperty().SetColor(0.8, 0.8, 0.8)
        return actor

    def _setBackGroundColor(self):
        self._renderer.GradientBackgroundOn()
        self._renderer.SetBackground(0.84, 0.85, 0.851)
        self._renderer.SetBackground2(0.32, 0.34, 0.43)

    def _addToolBar(self):
        self._toolBar = QToolBar()
        self._addIcons(resource.file('graphicsIcons'))

        self._actionAxesOnOff = QAction(self._iconAxesOn, 'Axes On/Off', self._main_window)
        self._actionAxesOnOff.setCheckable(True)
        self._actionAxesOnOff.setChecked(self._axesOn)
        self._toolBar.addAction(self._actionAxesOnOff)

        self._actionOriginAxesOnOff = QAction(self._iconOriginAxesOn, 'Origin Axes On/Off', self._main_window)
        self._actionOriginAxesOnOff.setCheckable(True)
        self._actionOriginAxesOnOff.setChecked(self._originAxesOn)
        self._toolBar.addAction(self._actionOriginAxesOnOff)

        self._actionOrthogonalOnOff = QAction(self._iconOrthogonalOn, 'Orthogonal/Perspective View', self._main_window)
        self._actionOrthogonalOnOff.setCheckable(True)
        self._actionOrthogonalOnOff.setChecked(self._orthogonalOn)
        self._toolBar.addAction(self._actionOrthogonalOnOff)

        self._toolBar.addSeparator()

        self._actionFit = QAction(self._iconFit, 'Fit', self._main_window)
        self._toolBar.addAction(self._actionFit)

        self._toolBar.addSeparator()

        self._actionPlusX = QAction(self._iconPlusX, '+X', self._main_window)
        self._toolBar.addAction(self._actionPlusX)
        self._actionMinusX = QAction(self._iconMinusX, '-X', self._main_window)
        self._toolBar.addAction(self._actionMinusX)

        self._actionPlusY = QAction(self._iconPlusY, '+Y', self._main_window)
        self._toolBar.addAction(self._actionPlusY)
        self._actionMinusY = QAction(self._iconMinusY, '-Y', self._main_window)
        self._toolBar.addAction(self._actionMinusY)

        self._actionPlusZ = QAction(self._iconPlusZ, '+Z', self._main_window)
        self._toolBar.addAction(self._actionPlusZ)
        self._actionMinusZ = QAction(self._iconMinusZ, '-Z', self._main_window)
        self._toolBar.addAction(self._actionMinusZ)

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
        self._iconAxesOn = self._newIcon(str(path / 'axesOn.png'))
        self._iconAxesOff = self._newIcon(str(path / 'axesOff.png'))

        self._iconOriginAxesOn = self._newIcon(str(path / 'originAxesOn.png'))
        self._iconOriginAxesOff = self._newIcon(str(path / 'originAxesOff.png'))

        self._iconOrthogonalOn = self._newIcon(str(path / 'orthogonalOn.png'))
        self._iconOrthogonalOff = self._newIcon(str(path / 'orthogonalOff.png'))

        self._iconFit = self._newIcon(str(path / 'fit.png'))

        self._iconPlusX = self._newIcon(str(path / 'plusX.png'))
        self._iconMinusX = self._newIcon(str(path / 'minusX.png'))
        self._iconPlusY = self._newIcon(str(path / 'plusY.png'))
        self._iconMinusY = self._newIcon(str(path / 'minusY.png'))
        self._iconPlusZ = self._newIcon(str(path / 'plusZ.png'))
        self._iconMinusZ = self._newIcon(str(path / 'minusZ.png'))

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
                a.GetProperty().SetLineWidth(1.0)
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
            if self._axesOn:
                self._hideAxes()
            else:
                self._showAxes()

        elif action == self._actionOriginAxesOnOff:
            if self._originAxesOn:
                self._hideOriginAxes()
            else:
                self._showOriginAxes()

        elif action == self._actionOrthogonalOnOff:
            if self._orthogonalOn:
                self._perspectiveMode()
            else:
                self._orthogonalMode()

        elif action == self._actionFit:
            self._fitCamera()
        elif action == self._actionPlusX:
            self._setCameraViewPlusX()
        elif action == self._actionMinusX:
            self._setCameraViewMinusX()
        elif action == self._actionPlusY:
            self._setCameraViewPlusY()
        elif action == self._actionMinusY:
            self._setCameraViewMinusY()
        elif action == self._actionPlusZ:
            self._setCameraViewPlusZ()
        elif action == self._actionMinusZ:
            self._setCameraViewMinusZ()

        elif action == self._actionCulling:
            if self._cullingOn:
                self._hideCulling()
            else:
                self._showCulling()

        self._widget.Render()

    def _showAxes(self):
        self._axesOn = True
        self._actionAxesOnOff.setIcon(self._iconAxesOn)
        self._actAxes.SetVisibility(True)
        self._axes.EnabledOn()

    def _hideAxes(self):
        self._axesOn = False
        self._actionAxesOnOff.setIcon(self._iconAxesOff)
        self._actAxes.SetVisibility(False)
        self._axes.EnabledOff()

    def _showOriginAxes(self):
        self._originAxesOn = True
        self._actionOriginAxesOnOff.setIcon(self._iconOriginAxesOn)
        self._renderer.AddActor(self._originActorX)
        self._renderer.AddActor(self._originActorY)
        self._renderer.AddActor(self._originActorZ)

    def _hideOriginAxes(self):
        self._originAxesOn = False
        self._actionOriginAxesOnOff.setIcon(self._iconOriginAxesOff)
        self._renderer.RemoveActor(self._originActorX)
        self._renderer.RemoveActor(self._originActorY)
        self._renderer.RemoveActor(self._originActorZ)

    def _orthogonalMode(self):
        self._orthogonalOn = True
        self._actionOrthogonalOnOff.setIcon(self._iconOrthogonalOn)
        self._renderer.GetActiveCamera().ParallelProjectionOn()

    def _perspectiveMode(self):
        self._orthogonalOn = False
        self._actionOrthogonalOnOff.setIcon(self._iconOrthogonalOff)
        self._renderer.GetActiveCamera().ParallelProjectionOff()

    def _fitCamera(self):
        if self._originAxesOn:
            self._hideOriginAxes()
            self._renderer.ResetCamera()
            self._showOriginAxes()
        else:
            self._renderer.ResetCamera()

    def _showCulling(self):
        self._cullingOn = True
        self._actionCulling.setIcon(self._iconCullingOn)

        actors = []
        for region in self._vtkMesh:
            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                actors.append(actorInfo.actor)

        for a in actors:
            a.GetProperty().FrontfaceCullingOn()

    def _hideCulling(self):
        self._cullingOn = False
        self._actionCulling.setIcon(self._iconCullingOff)

        actors = []
        for region in self._vtkMesh:
            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                actors.append(actorInfo.actor)

        for a in actors:
            a.GetProperty().FrontfaceCullingOff()

    def _addCamera(self):
        self.camera = vtkCamera()
        self._renderer.SetActiveCamera(self.camera)

    def _setCameraPosition(self, pos=(0.0, 0.0, 1.0), focal=(0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0)):
        self.camera.SetPosition(pos)
        self.camera.SetFocalPoint(focal)
        self.camera.SetViewUp(up)

        # if self.bAlwaysFit:
        #     self.renderer.ResetCamera()
        return

    def _setCameraViewPlusX(self):
        self._setCameraPosition((0, 0, 1), (0, 0, 0), (0, 1, 0))

    def _setCameraViewMinusX(self):
        self._setCameraPosition((0, 0, -1), (0, 0, 0), (0, 1, 0))

    def _setCameraViewPlusY(self):
        self._setCameraPosition((0, 0, -1), (0, 0, 0), (1, 0, 0))

    def _setCameraViewMinusY(self):
        self._setCameraPosition((0, 0, 1), (0, 0, 0), (1, 0, 0))

    def _setCameraViewPlusZ(self):
        self._setCameraPosition((0, 1, 0), (0, 0, 0), (1, 0, 0))

    def _setCameraViewMinusZ(self):
        self._setCameraPosition((0, -1, 0), (0, 0, 0), (1, 0, 0))

    def _setCameraView(self, cameraView):
        if cameraView == CAMERA_VIEW_PLUS_X:
            self._setCameraViewPlusX()
        elif cameraView == CAMERA_VIEW_MINUS_X:
            self._setCameraViewMinusX()
        elif cameraView == CAMERA_VIEW_PLUS_Y:
            self._setCameraViewPlusY()
        elif cameraView == CAMERA_VIEW_MINUS_Y:
            self._setCameraViewMinusY()
        elif cameraView == CAMERA_VIEW_PLUS_Z:
            self._setCameraViewPlusZ()
        elif cameraView == CAMERA_VIEW_MINUS_Z:
            self._setCameraViewMinusZ()
