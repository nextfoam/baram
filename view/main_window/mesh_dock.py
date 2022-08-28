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
from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer, vtkCamera
from vtkmodules.vtkIOGeometry import vtkOpenFOAMReader
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkCommonDataModel import vtkCompositeDataSet
from vtkmodules.vtkCommonColor import vtkNamedColors
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

    actor = vtk.vtkQuadricLODActor()    # vtkActor()
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
        self._axesActor = None

        self._originAxesOn = False
        self._originActor = None

        self._cubeAxesOn = False
        self._cubeAxesActor = None

        self._orthogonalViewOn = True
        self._displayMode = DISPLAY_MODE_SURFACE_EDGE
        self._cullingOn = False

        self.reloadMesh.connect(self.showOpenFoamMesh, Qt.ConnectionType.QueuedConnection)
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

            self._addCamera()

            self._namedColors = vtkNamedColors()

            self._graphicsPage = QVBoxLayout()
            self._graphicsPage.setSpacing(0)
            self._graphicsPage.setContentsMargins(6, 0, 6, 6)

            self._addToolBar()
            self._graphicsPage.addWidget(self._toolBar)
            self._graphicsPage.addWidget(self._widget)
            frame = QFrame()
            frame.setLayout(self._graphicsPage)
            self.setWidget(frame)

            self._setDefaults()

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

        if self._cubeAxesOn:
            self._showCubeAxes()

        if self._originAxesOn:
            self._showOriginAxes()

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

    def _setDefaults(self):
        self._actionAxesOnOff.setChecked(self._axesOn)
        self._actionOriginAxesOnOff.setChecked(self._originAxesOn)
        self._actionCubeAxesOnOff.setChecked(self._cubeAxesOn)
        self._actionOrthogonalViewOnOff.setChecked(self._orthogonalViewOn)

        self._showAxes()

        self._setBackGroundColorGradient()
        # self._setBackGroundColorSolid()

        self._orthogonalView()

    def _getAllActor(self):
        actors = []
        for region in self._vtkMesh:
            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                actors.append(actorInfo.actor)
        return actors

    def _addAxes(self):
        self._axesActor = vtk.vtkAxesActor()
        self._axesActor.SetVisibility(True)

        self._axesActor.SetShaftTypeToCylinder()
        self._axesActor.SetCylinderResolution(8)
        self._axesActor.SetNormalizedShaftLength(0.8, 0.8, 0.8)
        self._axesActor.SetConeResolution(8)
        self._axesActor.SetNormalizedTipLength(0.3, 0.3, 0.3)

        self._axesActor.SetNormalizedLabelPosition(1.0, 1.0, 1.0)

        self._axes = vtk.vtkOrientationMarkerWidget()
        self._axes.SetViewport(0.0, 0.0, 0.2, 0.2)  # (x, y, width, height)
        self._axes.SetOrientationMarker(self._axesActor)
        self._axes.SetInteractor(self._widget)

        self._axes.EnabledOn()
        self._axes.InteractiveOn()

    def _addOriginAxes(self, size=10.0):
        self._originActor = vtk.vtkAxesActor()
        self._originActor.SetVisibility(True)

        self._originActor.SetConeRadius(0.2)
        self._originActor.SetShaftTypeToLine()
        self._originActor.SetTotalLength(size, size, size)

        self._originActor.SetNormalizedLabelPosition(1.0, 1.0, 1.0)

        self._originAxes = vtk.vtkOrientationMarkerWidget()
        self._originAxes.SetViewport(0.0, 0.0, 0.2, 0.2)
        self._originAxes.SetOrientationMarker(self._originActor)
        self._originAxes.SetInteractor(self._widget)

    def _addCubeAxes(self, bounds):
        axisXColor = self._namedColors.GetColor3d("Salmon")
        axisYColor = self._namedColors.GetColor3d("PaleGreen")
        axisZColor = self._namedColors.GetColor3d("LightSkyBlue")

        self._cubeAxesActor = vtkCubeAxesActor()
        self._cubeAxesActor.SetUseTextActor3D(1)
        self._cubeAxesActor.SetBounds(bounds)
        self._cubeAxesActor.SetCamera(self._renderer.GetActiveCamera())

        self._cubeAxesActor.GetTitleTextProperty(0).SetColor(axisXColor)
        self._cubeAxesActor.GetTitleTextProperty(0).SetFontSize(48)
        self._cubeAxesActor.GetLabelTextProperty(0).SetColor(axisXColor)

        self._cubeAxesActor.GetTitleTextProperty(1).SetColor(axisYColor)
        self._cubeAxesActor.GetTitleTextProperty(1).SetFontSize(48)
        self._cubeAxesActor.GetLabelTextProperty(1).SetColor(axisYColor)

        self._cubeAxesActor.GetTitleTextProperty(2).SetColor(axisZColor)
        self._cubeAxesActor.GetTitleTextProperty(2).SetFontSize(48)
        self._cubeAxesActor.GetLabelTextProperty(2).SetColor(axisZColor)

        self._cubeAxesActor.DrawXGridlinesOn()
        self._cubeAxesActor.DrawYGridlinesOn()
        self._cubeAxesActor.DrawZGridlinesOn()
        self._cubeAxesActor.SetGridLineLocation(self._cubeAxesActor.VTK_GRID_LINES_FURTHEST)

        self._cubeAxesActor.XAxisMinorTickVisibilityOff()
        self._cubeAxesActor.YAxisMinorTickVisibilityOff()
        self._cubeAxesActor.ZAxisMinorTickVisibilityOff()

        self._cubeAxesActor.SetFlyModeToStaticEdges()

    def _drawLine(self, startPoint=(-1.0, 0.0, 0.0), endPoint=(1.0, 0.0, 0.0), color=(0.8, 0.8, 0.8)):
        lineSource = vtkLineSource()
        lineSource.SetPoint1(startPoint)
        lineSource.SetPoint2(endPoint)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(lineSource.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetLineWidth(1.0)
        actor.GetProperty().SetColor(color)
        return actor

    def _setBackGroundColorSolid(self):
        self._renderer.SetBackground(0.32, 0.34, 0.43)

    def _setBackGroundColorGradient(self):
        self._renderer.GradientBackgroundOn()
        self._renderer.SetBackground(0.82, 0.82, 0.82)
        self._renderer.SetBackground2(0.22, 0.24, 0.33)

    def _addToolBar(self):
        self._toolBar = QToolBar()
        self._addIcons(resource.file('graphicsIcons'))

        self._actionAxesOnOff = QAction(self._iconAxesOn, 'Axes On/Off', self._main_window)
        self._actionAxesOnOff.setCheckable(True)
        self._toolBar.addAction(self._actionAxesOnOff)

        self._actionOriginAxesOnOff = QAction(self._iconOriginAxesOff, 'Origin Axes On/Off', self._main_window)
        self._actionOriginAxesOnOff.setCheckable(True)
        self._toolBar.addAction(self._actionOriginAxesOnOff)

        self._actionCubeAxesOnOff = QAction(self._iconCubeAxesOff, 'Cube Axes On/Off', self._main_window)
        self._actionCubeAxesOnOff.setCheckable(True)
        self._toolBar.addAction(self._actionCubeAxesOnOff)

        self._actionOrthogonalViewOnOff = QAction(self._iconOrthogonalViewOn, 'Orthogonal/Perspective View', self._main_window)
        self._actionOrthogonalViewOnOff.setCheckable(True)
        self._toolBar.addAction(self._actionOrthogonalViewOnOff)

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

        self._iconCubeAxesOn = self._newIcon(str(path / 'cubeAxesOn.png'))
        self._iconCubeAxesOff = self._newIcon(str(path / 'cubeAxesOff.png'))

        self._iconOrthogonalViewOn = self._newIcon(str(path / 'orthogonalOn.png'))
        self._iconOrthogonalViewOff = self._newIcon(str(path / 'orthogonalOff.png'))

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
        actors = self._getAllActor()
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

        elif action == self._actionCubeAxesOnOff:
            if self._cubeAxesOn:
                self._hideCubeAxes()
            else:
                self._showCubeAxes()

        elif action == self._actionOrthogonalViewOnOff:
            if self._orthogonalViewOn:
                self._perspectiveView()
            else:
                self._orthogonalView()

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
        if self._axesActor is None:
            self._addAxes()
        self._axesOn = True
        self._actionAxesOnOff.setIcon(self._iconAxesOn)
        self._axesActor.SetVisibility(True)
        self._axes.EnabledOn()

    def _hideAxes(self):
        if self._axesActor is not None:
            self._axesOn = False
            self._actionAxesOnOff.setIcon(self._iconAxesOff)
            self._axesActor.SetVisibility(False)
            self._axes.EnabledOff()

    def _showOriginAxes(self):
        if self._originActor is not None:
            self._renderer.RemoveActor(self._originActor)

        bounds = self.getMeshTotalBounds()
        xSize = abs(bounds[1]-bounds[0]) * 2.0
        ySize = abs(bounds[3]-bounds[2]) * 2.0
        zSize = abs(bounds[5]-bounds[4]) * 2.0
        maxSize = max(xSize, ySize, zSize)

        self._addOriginAxes(maxSize)
        self._originAxesOn = True
        self._actionOriginAxesOnOff.setIcon(self._iconOriginAxesOn)
        self._renderer.AddActor(self._originActor)

    def _hideOriginAxes(self):
        if self._originActor is not None:
            self._originAxesOn = False
            self._actionOriginAxesOnOff.setIcon(self._iconOriginAxesOff)
            self._renderer.RemoveActor(self._originActor)

    def _orthogonalView(self):
        self._orthogonalViewOn = True
        self._actionOrthogonalViewOnOff.setIcon(self._iconOrthogonalViewOn)
        self._renderer.GetActiveCamera().ParallelProjectionOn()

    def _perspectiveView(self):
        self._orthogonalViewOn = False
        self._actionOrthogonalViewOnOff.setIcon(self._iconOrthogonalViewOff)
        self._renderer.GetActiveCamera().ParallelProjectionOff()

    def _showCubeAxes(self):
        if self._cubeAxesActor is not None:
            self._renderer.RemoveActor(self._cubeAxesActor)
        self._cubeAxesOn = True
        self._actionCubeAxesOnOff.setIcon(self._iconCubeAxesOn)
        self._addCubeAxes(self.getMeshTotalBounds())
        self._renderer.AddActor(self._cubeAxesActor)

    def getMeshTotalBounds(self) -> list:
        checkFirst = True
        bounds = [0, 0, 0, 0, 0, 0]
        for region in self._vtkMesh:
            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                getBounds = actorInfo.actor.GetBounds()
                if checkFirst:
                    bounds = list(getBounds)
                    checkFirst = False
                else:
                    bounds[0] = min(bounds[0], getBounds[0])
                    bounds[1] = max(bounds[1], getBounds[1])
                    bounds[2] = min(bounds[2], getBounds[2])
                    bounds[3] = max(bounds[3], getBounds[3])
                    bounds[4] = min(bounds[4], getBounds[4])
                    bounds[5] = max(bounds[5], getBounds[5])
        return bounds

    def getMeshCenterPoint(self) -> list:
        center = []
        bounds = self.getMeshTotalBounds()
        center.append((bounds[0] + bounds[1]) * 0.5)
        center.append((bounds[2] + bounds[3]) * 0.5)
        center.append((bounds[4] + bounds[5]) * 0.5)
        return center

    def _hideCubeAxes(self):
        if self._cubeAxesActor is not None:
            self._cubeAxesOn = False
            self._actionCubeAxesOnOff.setIcon(self._iconCubeAxesOff)
            self._renderer.RemoveActor(self._cubeAxesActor)

    def _fitCamera(self):
        if self._originAxesOn:
            self._hideOriginAxes()
            self._renderer.ResetCamera()
            self._showOriginAxes()
        else:
            self._renderer.ResetCamera()

        if self._cubeAxesOn:
            self._showCubeAxes()

    def _showCulling(self):
        self._cullingOn = True
        self._actionCulling.setIcon(self._iconCullingOn)

        actors = self._getAllActor()
        for a in actors:
            a.GetProperty().FrontfaceCullingOn()

    def _hideCulling(self):
        self._cullingOn = False
        self._actionCulling.setIcon(self._iconCullingOff)

        actors = self._getAllActor()
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
        cameraPosition = [0.0, 0.0, 0.0]
        centers = self.getMeshCenterPoint()
        cameraPosition[0:3] = centers[0:3]
        cameraPosition[2] = centers[2] + 2.0

        self._setCameraPosition(tuple(cameraPosition), tuple(centers), (0, 1, 0))
        self._fitCamera()

    def _setCameraViewMinusX(self):
        cameraPosition = [0.0, 0.0, 0.0]
        centers = self.getMeshCenterPoint()
        cameraPosition[0:3] = centers[0:3]
        cameraPosition[2] = centers[2] - 2.0

        self._setCameraPosition(tuple(cameraPosition), tuple(centers), (0, 1, 0))
        self._fitCamera()

    def _setCameraViewPlusY(self):
        cameraPosition = [0.0, 0.0, 0.0]
        centers = self.getMeshCenterPoint()
        cameraPosition[0:3] = centers[0:3]
        cameraPosition[2] = centers[2] - 2.0

        self._setCameraPosition(tuple(cameraPosition), tuple(centers), (1, 0, 0))
        self._fitCamera()

    def _setCameraViewMinusY(self):
        cameraPosition = [0.0, 0.0, 0.0]
        centers = self.getMeshCenterPoint()
        cameraPosition[0:3] = centers[0:3]
        cameraPosition[2] = centers[2] + 2.0

        self._setCameraPosition(tuple(cameraPosition), tuple(centers), (1, 0, 0))
        self._fitCamera()

    def _setCameraViewPlusZ(self):
        cameraPosition = [0.0, 0.0, 0.0]
        centers = self.getMeshCenterPoint()
        cameraPosition[0:3] = centers[0:3]
        cameraPosition[0] = centers[0] - 2.0

        self._setCameraPosition(tuple(cameraPosition), tuple(centers), (0, 1, 0))
        self._fitCamera()

    def _setCameraViewMinusZ(self):
        cameraPosition = [0.0, 0.0, 0.0]
        centers = self.getMeshCenterPoint()
        cameraPosition[0:3] = centers[0:3]
        cameraPosition[0] = centers[0] + 2.0

        self._setCameraPosition(tuple(cameraPosition), tuple(centers), (0, 1, 0))
        self._fitCamera()

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
