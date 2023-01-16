#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os
import platform
import subprocess
from typing import TYPE_CHECKING
from typing import Optional
from enum import Enum, auto

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QToolBar, QVBoxLayout, QWidgetAction, QFileDialog
from PySide6.QtGui import QAction, QIcon

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkFiltersSources import vtkLineSource
from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer, vtkCamera, vtkPropPicker
from vtkmodules.vtkRenderingCore import vtkCoordinate
from vtkmodules.vtkCommonColor import vtkNamedColors
# load implementations for rendering and interaction factory classes
import vtkmodules.vtkRenderingOpenGL2
import vtkmodules.vtkInteractionStyle
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera

from app import app
from coredb.app_settings import AppSettings
from coredb.project import Project
from resources import resource
from openfoam.file_system import FileSystem
from .tabified_dock import TabifiedDock
if TYPE_CHECKING:
    from .main_window import MainWindow

import vtk

# To fix middle button issue in vtkmodules
# Qt.MidButton that is not available in PySide6 is use in QVTKRenderWindowInteractor
# Remove this line when vtk 9.2.2 or later is used
Qt.MidButton = Qt.MiddleButton

colors = vtkNamedColors()


class DisplayMode(Enum):
    DISPLAY_MODE_POINTS         = 0
    DISPLAY_MODE_WIREFRAME      = auto()
    DISPLAY_MODE_SURFACE        = auto()
    DISPLAY_MODE_SURFACE_EDGE   = auto()
    DISPLAY_MODE_FEATURE        = auto()


class MouseInteractorHighLightActor(vtkInteractorStyleTrackballCamera):
    def __init__(self, parent=None):
        self.AddObserver('LeftButtonPressEvent', self._leftButtonPressEvent)
        self.AddObserver('LeftButtonReleaseEvent', self._leftButtonReleaseEvent)
        self.AddObserver('MouseWheelForwardEvent', self._mouseWheelForwardEvent)
        self.AddObserver('MouseWheelBackwardEvent', self._mouseWheelBackwardEvent)
        self.AddObserver('InteractionEvent', self._interactionEvent)

        self._parent = parent
        self._pressPos = None

    def _leftButtonPressEvent(self, obj, event):
        self._pressPos = self.GetInteractor().GetEventPosition()
        self.OnLeftButtonDown()

    def _leftButtonReleaseEvent(self, obj, event):
        clickPos = self.GetInteractor().GetEventPosition()

        if clickPos == self._pressPos:
            picker = vtkPropPicker()
            picker.Pick(clickPos[0], clickPos[1], 0, self.GetDefaultRenderer())

            self._parent.actorPicked.emit(picker.GetActor())

        self.OnLeftButtonUp()

    def _mouseWheelForwardEvent(self, obj, event):
        super().OnMouseWheelForward()
        self._parent.resizeOriginActor()

    def _mouseWheelBackwardEvent(self, obj, event):
        super().OnMouseWheelBackward()
        self._parent.resizeOriginActor()

    def _interactionEvent(self, obj, event):
        self._parent.resizeOriginActor()

    def getOriginActorLength(self):
        p0 = [0, 0, 0]
        p1 = [0, 0, 0, 0]
        p2 = [0, 0, 0, 0]

        x, y = self.GetDefaultRenderer().GetSize()

        self.ComputeWorldToDisplay(self.GetDefaultRenderer(), 0, 0, 0, p0)
        self.ComputeDisplayToWorld(self.GetDefaultRenderer(), 0, 0, p0[2], p1)
        self.ComputeDisplayToWorld(self.GetDefaultRenderer(), x, y, p0[2], p2)

        length = abs(p1[0] - p2[0]) if x < y else abs(p1[1] - p2[1])

        return length * 0.4


class RenderWindowInteractor(QVTKRenderWindowInteractor):
    def Finalize(self):
        if self._RenderWindow is not None:
            self._RenderWindow.Finalize()
            self._RenderWindow = None


class MeshDock(TabifiedDock):
    reloadMesh = Signal()
    meshLoaded = Signal()
    actorPicked = Signal(vtkActor)

    def __init__(self, parent: Optional['MainWindow'] = None):
        super().__init__(parent)

        self._main_window = parent

        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._widget = None
        self._renderer = None

        self._axesOn = True
        self._axesActor = None

        self._originAxesOn = False
        self._originActor = None

        self._cubeAxesActor = None

        self._orthogonalViewOn = False
        self._cullingOn = False

        self._meshOn = False
        self._model = None

        self._main_window.windowClosed.connect(self._mainWindowClosed)

        frame = QFrame()

        self._style = MouseInteractorHighLightActor(self)
        self._widget = RenderWindowInteractor(frame)
        self._widget.SetInteractorStyle(self._style)

        self._renderer = vtkRenderer()
        self._widget.GetRenderWindow().AddRenderer(self._renderer)
        self._style.SetDefaultRenderer(self._renderer)
        self.actorPicked.connect(self._actorPicked)

        self._widget.Initialize()
        self._widget.Start()

        self._addCamera()

        self._graphicsPage = QVBoxLayout()
        self._graphicsPage.setSpacing(0)
        self._graphicsPage.setContentsMargins(6, 0, 6, 6)

        self._addToolBar()
        self._graphicsPage.addWidget(self._toolBar)
        self._graphicsPage.addWidget(self._widget)
        frame.setLayout(self._graphicsPage)
        self.setWidget(frame)

        self._setDefaults()

        self._translate()

    def setModel(self, model):
        if self._model:
            self._model.deactivate()

        self._model = model
        if self._model:
            self._model.activate()

        self.render()

    def closeEvent(self, event):
        if app.closed():
            event.accept()
        else:
            self.hide()
            event.ignore()

    def _mainWindowClosed(self, result):
        self._widget.close()

    def addActor(self, actor):
        self._renderer.AddActor(actor)

    def removeActor(self, actor):
        self._renderer.RemoveActor(actor)

    def update(self):
        self._widget.Render()

    def render(self):
        if self._cubeAxesActor:
            self._showCubeAxes()

        if self._originAxesOn:
            self._showOriginAxes()

        self._fitCamera()
        self._widget.Render()

    def displayMode(self):
        return self._displayModeCombo.currentIndex()

    def resizeOriginActor(self):
        if self._originActor:
            length = self._style.getOriginActorLength()
            self._originActor.SetTotalLength(length, length, length)
            self._widget.Render()

    def _translate(self):
        self.setWindowTitle(self.tr("Mesh"))
        self._actionRunParaview.setText(self.tr('Run ParaView'))
        self._actionAxesOnOff.setText(self.tr('Axes On/Off'))
        self._actionOriginAxesOnOff.setText(self.tr('Origin Axes On/Off'))
        self._actionCubeAxesOnOff.setText(self.tr('Cube Axes On/Off'))
        self._actionOrthogonalViewOnOff.setText(self.tr('Orthogonal/Perspective View'))
        self._actionFit.setText(self.tr('Fit'))
        self._actionRotate.setText(self.tr('Rotate'))
        self._actionCulling.setText(self.tr('Front-face Culling'))

        displayModes = {
            DisplayMode.DISPLAY_MODE_POINTS.value       : self.tr('Points'),
            DisplayMode.DISPLAY_MODE_WIREFRAME.value    : self.tr('Wireframe'),
            DisplayMode.DISPLAY_MODE_SURFACE.value      : self.tr('Surface'),
            DisplayMode.DISPLAY_MODE_SURFACE_EDGE.value : self.tr('SurfaceEdge'),
            DisplayMode.DISPLAY_MODE_FEATURE .value     : self.tr('Feature'),
        }

        for index, text in displayModes.items():
            self._displayModeCombo.setItemText(index, text)

    def _setDefaults(self):
        self._actionAxesOnOff.setChecked(self._axesOn)
        self._actionOriginAxesOnOff.setChecked(self._originAxesOn)
        self._actionCubeAxesOnOff.setChecked(self._cubeAxesActor is not None)
        self._actionOrthogonalViewOnOff.setChecked(self._orthogonalViewOn)

        self._showAxes()

        self._setBackGroundColorGradient()
        # self._setBackGroundColorSolid()

        self._perspectiveView()

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

        self._originActor.SetConeRadius(0.1)
        self._originActor.SetShaftTypeToLine()
        self._originActor.SetNormalizedShaftLength(0.9, 0.9, 0.9)
        self._originActor.SetNormalizedTipLength(0.1, 0.1, 0.1)
        self._originActor.SetNormalizedLabelPosition(1.0, 1.0, 1.0)
        # xLabel = self._originActor.GetCaptionTextProperty().SetFontSize(1)
        self.resizeOriginActor()

        # self._originAxes = vtk.vtkOrientationMarkerWidget()
        # self._originAxes.SetViewport(0.0, 0.0, 0.2, 0.2)
        # self._originAxes.SetOrientationMarker(self._originActor)
        # self._originAxes.SetInteractor(self._widget)

    def _addCubeAxes(self, bounds):
        axisXColor = colors.GetColor3d("Salmon")
        axisYColor = colors.GetColor3d("PaleGreen")
        axisZColor = colors.GetColor3d("LightSkyBlue")

        self._cubeAxesActor = vtkCubeAxesActor()
        self._cubeAxesActor.SetUseTextActor3D(1)
        self._cubeAxesActor.SetBounds(bounds)
        self._cubeAxesActor.SetCamera(self._renderer.GetActiveCamera())

        self._cubeAxesActor.GetTitleTextProperty(0).SetColor(axisXColor)
        self._cubeAxesActor.GetTitleTextProperty(0).SetFontSize(48)
        self._cubeAxesActor.GetTitleTextProperty(0).BoldOn()
        self._cubeAxesActor.GetLabelTextProperty(0).SetColor(axisXColor)
        self._cubeAxesActor.GetLabelTextProperty(0).BoldOn()

        self._cubeAxesActor.GetTitleTextProperty(1).SetColor(axisYColor)
        self._cubeAxesActor.GetTitleTextProperty(1).SetFontSize(48)
        self._cubeAxesActor.GetTitleTextProperty(1).BoldOn()
        self._cubeAxesActor.GetLabelTextProperty(1).SetColor(axisYColor)
        self._cubeAxesActor.GetLabelTextProperty(1).BoldOn()

        self._cubeAxesActor.GetTitleTextProperty(2).SetColor(axisZColor)
        self._cubeAxesActor.GetTitleTextProperty(2).SetFontSize(48)
        self._cubeAxesActor.GetTitleTextProperty(2).BoldOn()
        self._cubeAxesActor.GetLabelTextProperty(2).SetColor(axisZColor)
        self._cubeAxesActor.GetLabelTextProperty(2).BoldOn()

        self._cubeAxesActor.DrawXGridlinesOn()
        self._cubeAxesActor.DrawYGridlinesOn()
        self._cubeAxesActor.DrawZGridlinesOn()
        self._cubeAxesActor.SetGridLineLocation(self._cubeAxesActor.VTK_GRID_LINES_FURTHEST)

        self._cubeAxesActor.XAxisMinorTickVisibilityOff()
        self._cubeAxesActor.YAxisMinorTickVisibilityOff()
        self._cubeAxesActor.ZAxisMinorTickVisibilityOff()

        self._cubeAxesActor.SetFlyModeToOuterEdges()

        self._renderer.AddActor(self._cubeAxesActor)

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

        self._actionRunParaview = QAction(self._iconRunParaview, '', self._main_window)
        self._toolBar.addAction(self._actionRunParaview)

        self._toolBar.addSeparator()

        self._actionAxesOnOff = QAction(self._iconAxesOn, '', self._main_window)
        self._actionAxesOnOff.setCheckable(True)
        self._toolBar.addAction(self._actionAxesOnOff)

        self._actionOriginAxesOnOff = QAction(self._iconOriginAxesOff, '', self._main_window)
        self._actionOriginAxesOnOff.setCheckable(True)
        self._toolBar.addAction(self._actionOriginAxesOnOff)

        self._actionCubeAxesOnOff = QAction(self._iconCubeAxes, '', self._main_window)
        self._actionCubeAxesOnOff.setCheckable(True)
        self._toolBar.addAction(self._actionCubeAxesOnOff)

        self._actionOrthogonalViewOnOff = QAction(self._iconOrthogonalViewOn, '', self._main_window)
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

        self._actionRotate = QAction(self._iconRotate, '', self._main_window)
        self._toolBar.addAction(self._actionRotate)

        self._toolBar.addSeparator()

        self._displayModeCombo = QComboBox()
        self._displayModeCombo.addItems(['Points', 'Wireframe', 'Surface', 'SurfaceEdge', 'Feature'])
        self._displayModeCombo.setCurrentIndex(DisplayMode.DISPLAY_MODE_SURFACE_EDGE.value)
        self._displayModeCombo.currentIndexChanged.connect(self._clickedVDisplayModeCombo)
        self._actionShowMode = QWidgetAction(self._main_window)
        self._actionShowMode.setDefaultWidget(self._displayModeCombo)
        self._toolBar.addAction(self._actionShowMode)

        self._toolBar.addSeparator()

        self._actionCulling = QAction(self._iconCullingOff, 'Front-face Culling', self._main_window)
        self._actionCulling.setCheckable(True)
        self._toolBar.addAction(self._actionCulling)
        self._toolBar.addSeparator()

        self._toolBar.actionTriggered[QAction].connect(self.clickedToolBar)

    def _addIcons(self, path):
        self._iconRunParaview = QIcon(str(path / 'ParaView.png'))

        self._iconAxesOn = QIcon(str(path / 'axesOn.png'))
        self._iconAxesOff = QIcon(str(path / 'axesOff.png'))

        self._iconOriginAxesOn = QIcon(str(path / 'originAxesOn.png'))
        self._iconOriginAxesOff = QIcon(str(path / 'originAxesOff.png'))

        self._iconCubeAxes = QIcon(str(path / 'ruler.ico'))

        self._iconOrthogonalViewOn = QIcon(str(path / 'orthogonalOn.png'))
        self._iconOrthogonalViewOff = QIcon(str(path / 'orthogonalOff.png'))

        self._iconFit = QIcon(str(resource.file('ionicons/expand.svg')))

        self._iconPlusX = QIcon(str(path / 'plusX.png'))
        self._iconMinusX = QIcon(str(path / 'minusX.png'))
        self._iconPlusY = QIcon(str(path / 'plusY.png'))
        self._iconMinusY = QIcon(str(path / 'minusY.png'))
        self._iconPlusZ = QIcon(str(path / 'plusZ.png'))
        self._iconMinusZ = QIcon(str(path / 'minusZ.png'))

        self._iconRotate = QIcon(str(resource.file('ionicons/reload.svg')))

        self._iconCullingOn = QIcon(str(path / 'cullingOn.png'))
        self._iconCullingOff = QIcon(str(path / 'cullingOff.png'))

    def _clickedVDisplayModeCombo(self, index):
        if self._model:
            self._model.changeDisplayMode(index)

        self._widget.Render()

    def clickedToolBar(self, action):
        if action == self._actionRunParaview:
            self._runParaview()

        elif action == self._actionAxesOnOff:
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
            if self._cubeAxesActor:
                self._hideCubeAxes()
            else:
                self._showCubeAxes()

            self._actionCubeAxesOnOff.setChecked(self._cubeAxesActor is not None)

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
        elif action == self._actionRotate:
            self.camera.Roll(-90)

        elif action == self._actionCulling:
            if self._cullingOn:
                self._hideCulling()
            else:
                self._showCulling()

        self._widget.Render()

    def _runParaview(self):
        casePath = ''
        _project = Project.instance()
        if _project.meshLoaded:
            casePath = FileSystem.foamFilePath()

        if platform.system() == 'Windows':
            path = AppSettings.getParaviewInstalledPath()
            if os.path.exists(path):
                subprocess.Popen([f'{path}', f'{casePath}'])
            else:
                path = ''
                findParaview = glob.glob('C:/Program Files/paraview*')
                if len(findParaview) == 1:
                    executeFile = f'{findParaview[0]}/bin/paraview.exe'
                    if os.path.exists(executeFile):
                        path = executeFile
                        AppSettings.updateParaviewInstalledPath(path)
                        subprocess.Popen([f'{path}', f'{casePath}'])

                if not path:
                    self._dialog = QFileDialog(self, self.tr('Select Paraview Program'), 'C:/Program Files', 'exe (*.exe)')
                    self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
                    self._dialog.accepted.connect(self._selectedExeFile)
                    self._dialog.open()
        else:
            subprocess.Popen([f'paraview', f'{casePath}'])

    def _selectedExeFile(self):
        casePath = ''
        _project = Project.instance()
        if _project.meshLoaded:
            casePath = FileSystem.foamFilePath()

        selectedFile = self._dialog.selectedFiles()[0]
        AppSettings.updateParaviewInstalledPath(selectedFile)
        subprocess.Popen([f'{selectedFile}', f'{casePath}'])

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
        if self._originActor:
            return
            # self._renderer.RemoveActor(self._originActor)

        if self._model:
            bounds = self._model.fullBounds()
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
        self._hideCubeAxes()

        if self._model:
            self._addCubeAxes(self._model.fullBounds())

    def getMeshCenterPoint(self) -> list:
        center = []
        bounds = self.getMeshTotalBounds()
        center.append((bounds[0] + bounds[1]) * 0.5)
        center.append((bounds[2] + bounds[3]) * 0.5)
        center.append((bounds[4] + bounds[5]) * 0.5)
        return center

    def _hideCubeAxes(self):
        if self._cubeAxesActor is not None:
            self._renderer.RemoveActor(self._cubeAxesActor)
            self._cubeAxesActor = None

    def _fitCamera(self):
        if self._originAxesOn:
            # self._hideOriginAxes()
            self._renderer.ResetCamera()
            # self._showOriginAxes()
        else:
            self._renderer.ResetCamera()

        if self._cubeAxesActor:
            self._showCubeAxes()

    def _showCulling(self):
        self._cullingOn = True
        self._actionCulling.setIcon(self._iconCullingOn)

        if self._model:
            self._model.showCulling()

    def _hideCulling(self):
        self._cullingOn = False
        self._actionCulling.setIcon(self._iconCullingOff)

        if self._model:
            self._model.hideCulling()

    def _addCamera(self):
        self.camera = vtkCamera()
        self._renderer.SetActiveCamera(self.camera)

    def _setCameraViewPlusX(self):
        d = self.camera.GetDistance()
        fx, fy, fz = self.camera.GetFocalPoint()
        self.camera.SetPosition(fx-d, fy, fz)
        self.camera.SetViewUp(0, 0, 1)

    def _setCameraViewMinusX(self):
        d = self.camera.GetDistance()
        fx, fy, fz = self.camera.GetFocalPoint()
        self.camera.SetPosition(fx+d, fy, fz)
        self.camera.SetViewUp(0, 0, 1)

    def _setCameraViewPlusY(self):
        d = self.camera.GetDistance()
        fx, fy, fz = self.camera.GetFocalPoint()
        self.camera.SetPosition(fx, fy-d, fz)
        self.camera.SetViewUp(0, 0, 1)

    def _setCameraViewMinusY(self):
        d = self.camera.GetDistance()
        fx, fy, fz = self.camera.GetFocalPoint()
        self.camera.SetPosition(fx, fy+d, fz)
        self.camera.SetViewUp(0, 0, 1)

    def _setCameraViewPlusZ(self):
        d = self.camera.GetDistance()
        fx, fy, fz = self.camera.GetFocalPoint()
        self.camera.SetPosition(fx, fy, fz-d)
        self.camera.SetViewUp(0, 1, 0)

    def _setCameraViewMinusZ(self):
        d = self.camera.GetDistance()
        fx, fy, fz = self.camera.GetFocalPoint()
        self.camera.SetPosition(fx, fy, fz+d)
        self.camera.SetViewUp(0, 1, 0)

    def _actorPicked(self, actor):
        self._model.actorPicked(actor)
