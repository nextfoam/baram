#!/usr/bin/env python
# -*- coding: utf-8 -*-

# A simple script to demonstrate the vtkCutter function

import math
import platform
import subprocess
from enum import Enum, auto
from typing import Optional
from pathlib import Path

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QFileDialog
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkCommand
# load implementations for rendering and interaction factory classes
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor, vtkCubeAxesActor
from vtkmodules.vtkRenderingCore import vtkActor, vtkRenderer, vtkPropPicker

from coredb.project import Project
from coredb.app_settings import AppSettings
from openfoam.file_system import FileSystem
from .rendering_view_ui import Ui_RenderingView

# To fix middle button issue in vtkmodules
# Qt.MidButton that is not available in PySide6 is use in QVTKRenderWindowInteractor
# Remove this line when vtk 9.2.2 or later is used
Qt.MidButton = Qt.MiddleButton

colors = vtkNamedColors()


class DisplayMode(Enum):
    DISPLAY_MODE_FEATURE        = 0
    DISPLAY_MODE_POINTS         = auto()
    DISPLAY_MODE_SURFACE        = auto()
    DISPLAY_MODE_SURFACE_EDGE   = auto()
    DISPLAY_MODE_WIREFRAME      = auto()


class RenderWindowInteractor(QVTKRenderWindowInteractor):
    def Finalize(self):
        if self._RenderWindow is not None:
            self._RenderWindow.Finalize()
            self._RenderWindow = None


class RenderingView(QWidget):
    actorPicked = Signal(vtkActor)
    renderingModeChanged = Signal(DisplayMode)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._ui = Ui_RenderingView()
        self._ui.setupUi(self)

        for mode in DisplayMode:
            self._ui.renderingMode.setItemData(mode.value, mode)

        self._dialog: Optional[QFileDialog] = None

        self._originActor: Optional[vtkActor] = None
        self._cubeAxesActor: Optional[vtkCubeAxesActor] = None

        self._pressPos = None

        self._style = vtkInteractorStyleTrackballCamera()
        self._widget = RenderWindowInteractor(self._ui.renderingFrame)
        self._widget.SetInteractorStyle(self._style)
        self._style.OnMouseWheelBackward()

        self._renderer = vtkRenderer()
        self._widget.GetRenderWindow().AddRenderer(self._renderer)
        # self._style.SetDefaultRenderer(self._renderer)

        self._widget.Initialize()
        self._widget.Start()

        self._renderer.GradientBackgroundOn()
        self._renderer.SetBackground(0.82, 0.82, 0.82)
        self._renderer.SetBackground2(0.22, 0.24, 0.33)

        self._ui.renderingFrame.layout().addWidget(self._widget)

        # To pick actors
        self._style.AddObserver(vtkCommand.LeftButtonPressEvent, self._leftButtonPressEvent)
        self._style.AddObserver(vtkCommand.LeftButtonReleaseEvent, self._leftButtonReleaseEvent)

        # To adjust origin axes size on zoom
        self._style.AddObserver(vtkCommand.MouseWheelForwardEvent, self._mouseWheelForwardEvent)
        self._style.AddObserver(vtkCommand.MouseWheelBackwardEvent, self._mouseWheelBackwardEvent)
        self._style.AddObserver(vtkCommand.InteractionEvent, self._interactionEvent)

        self._connectSignalsSlots()

    def renderingMode(self):
        return self._ui.renderingMode.currentData()

    def addActor(self, actor: vtkActor):
        self._renderer.AddActor(actor)

    def removeActor(self, actor):
        self._renderer.RemoveActor(actor)

    def refresh(self):
        self._widget.Render()

    def fitCamera(self):
        self._renderer.ResetCamera()
        self._widget.Render()

    def close(self):
        self._widget.close()

        return super().close()

    def _connectSignalsSlots(self):
        self._ui.paraview.clicked.connect(self._runParaview)
        self._ui.plusX.clicked.connect(self._plusXClicked)
        self._ui.plusY.clicked.connect(self._plusYClicked)
        self._ui.plusZ.clicked.connect(self._plusZClicked)
        self._ui.minusX.clicked.connect(self._minusXClicked)
        self._ui.minusY.clicked.connect(self._minusYClicked)
        self._ui.minusZ.clicked.connect(self._minusZClicked)
        self._ui.axis.toggled.connect(self._axisToggled)
        self._ui.cubeAxis.toggled.connect(self._cubeAxisToggled)
        self._ui.fit.clicked.connect(self._fitCameraClicked)
        self._ui.perspective.toggled.connect(self._perspectiveToggled)
        self._ui.renderingMode.currentIndexChanged.connect(self._renderingModeChanged)
        self._ui.rotate.clicked.connect(self._rotateClicked)

    def _turnCamera(self, orientation: tuple[int, int, int], up: tuple[int, int, int]):
        camera = self._renderer.GetActiveCamera()
        d = camera.GetDistance()
        fx, fy, fz = camera.GetFocalPoint()
        camera.SetPosition(fx+orientation[0]*d, fy+orientation[1]*d, fz+orientation[2]*d)
        camera.SetViewUp(up[0], up[1], up[2])

    def _runParaview(self):
        casePath = ''
        if Project.instance().meshLoaded:
            casePath = FileSystem.foamFilePath()

        if platform.system() == 'Windows':
            # AppSettings has the paraview path.
            if path := AppSettings.getParaviewInstalledPath():
                if Path(path).exists():
                    subprocess.Popen([path, casePath])
                    return

            # Search the unique paraview executable file.
            paraviewHomes = list(Path('C:/Program Files').glob('paraview*'))
            if len(paraviewHomes) == 1:
                path = paraviewHomes[0] / 'bin/paraview.exe'
                if path.exists():
                    AppSettings.updateParaviewInstalledPath(path)
                    subprocess.Popen([path, casePath])
                    return

            # The system has no paraview executables or more than one.
            self._dialog = QFileDialog(self, self.tr('Select Paraview Program'), 'C:/Program Files', 'exe (*.exe)')
            self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
            self._dialog.fileSelected.connect(self._paraviewFileSelected)
            self._dialog.open()
        else:
            subprocess.Popen(['paraview', casePath])

    def _paraviewFileSelected(self, file):
        casePath = FileSystem.foamFilePath()
        AppSettings.updateParaviewInstalledPath(file)
        subprocess.Popen([f'{file}', f'{casePath}'])

    def _plusXClicked(self):
        self._turnCamera((-1, 0, 0), (0, 0, 1))
        self._widget.Render()

    def _plusYClicked(self):
        self._turnCamera((0, -1, 0), (0, 0, 1))
        self._widget.Render()

    def _plusZClicked(self):
        self._turnCamera((0, 0, -1), (0, 1, 0))
        self._widget.Render()

    def _minusXClicked(self):
        self._turnCamera((1, 0, 0), (0, 0, 1))
        self._widget.Render()

    def _minusYClicked(self):
        self._turnCamera((0, 1, 0), (0, 0, 1))
        self._widget.Render()

    def _minusZClicked(self):
        self._turnCamera((0, 0, 1), (0, 1, 0))
        self._widget.Render()

    def _fitCameraClicked(self):
        self.fitCamera()

    def _rotateClicked(self):
        self._renderer.GetActiveCamera().Roll(-90)
        self._widget.Render()

    def _perspectiveToggled(self, checked):
        if checked:
            self._renderer.GetActiveCamera().ParallelProjectionOff()
        else:
            self._renderer.GetActiveCamera().ParallelProjectionOn()
        self._widget.Render()

    def _axisToggled(self, checked):
        if checked:
            self._showOriginAxes()
        else:
            self._hideOriginAxes()

        self._resizeOriginAxis()
        self._widget.Render()

    def _cubeAxisToggled(self, checked):
        if checked:
            self._showCubeAxes()
        else:
            self._hideCubeAxes()
        self._widget.Render()

    def _getBounds(self):
        if self._originActor is not None:
            self._originActor.SetVisibility(False)

        bounds = self._renderer.ComputeVisiblePropBounds()

        if self._originActor is not None:
            self._originActor.SetVisibility(True)

        return bounds

    def _showCubeAxes(self):
        if self._cubeAxesActor is not None:
            return

        self._cubeAxesActor = vtkCubeAxesActor()
        self._cubeAxesActor.SetUseTextActor3D(1)
        self._cubeAxesActor.SetBounds(self._getBounds())
        self._cubeAxesActor.SetCamera(self._renderer.GetActiveCamera())

        axisColors = (
            colors.GetColor3d("Salmon"),
            colors.GetColor3d("PaleGreen"),
            colors.GetColor3d("LightSkyBlue")
        )
        for i in range(3):
            self._cubeAxesActor.GetTitleTextProperty(i).SetColor(axisColors[i])
            self._cubeAxesActor.GetTitleTextProperty(i).SetFontSize(48)
            self._cubeAxesActor.GetTitleTextProperty(i).BoldOn()
            self._cubeAxesActor.GetLabelTextProperty(i).SetColor(axisColors[i])
            self._cubeAxesActor.GetLabelTextProperty(i).BoldOn()

        self._cubeAxesActor.DrawXGridlinesOn()
        self._cubeAxesActor.DrawYGridlinesOn()
        self._cubeAxesActor.DrawZGridlinesOn()
        self._cubeAxesActor.SetGridLineLocation(self._cubeAxesActor.VTK_GRID_LINES_FURTHEST)

        self._cubeAxesActor.XAxisMinorTickVisibilityOff()
        self._cubeAxesActor.YAxisMinorTickVisibilityOff()
        self._cubeAxesActor.ZAxisMinorTickVisibilityOff()

        self._cubeAxesActor.SetFlyModeToOuterEdges()

        self._renderer.AddActor(self._cubeAxesActor)

    def _hideCubeAxes(self):
        if self._cubeAxesActor is not None:
            self._renderer.RemoveActor(self._cubeAxesActor)
            self._cubeAxesActor = None

    def _showOriginAxes(self):
        if self._originActor is not None:
            return

        self._originActor = vtkAxesActor()

        self._originActor.SetVisibility(True)
        self._originActor.AxisLabelsOff()
        self._originActor.SetConeRadius(0.2)
        self._originActor.SetShaftTypeToLine()
        self._originActor.SetNormalizedShaftLength(0.9, 0.9, 0.9)
        self._originActor.SetNormalizedTipLength(0.1, 0.1, 0.1)
        self._originActor.SetNormalizedLabelPosition(1.0, 1.0, 1.0)

        self._renderer.AddActor(self._originActor)

    def _hideOriginAxes(self):
        if self._originActor is not None:
            self._renderer.RemoveActor(self._originActor)
            self._originActor = None

    def _resizeOriginAxis(self):
        if self._originActor:
            camera = self._renderer.GetActiveCamera()

            d = camera.GetDirectionOfProjection()
            p = camera.GetPosition()
            distance = -p[0]*d[0]-p[1]*d[1]-p[2]*d[2]

            degree = camera.GetViewAngle()
            radian = math.radians(degree/3.0)
            length = distance * math.tan(radian)

            # length = self._style.getOriginActorLength()
            self._originActor.SetTotalLength(length, length, length)

    def _renderingModeChanged(self, index):
        print(f'renderingModechanged to {DisplayMode(index)}')

        # self._widget.Render()
        self.renderingModeChanged.emit(DisplayMode(index))

    def _leftButtonPressEvent(self, obj, event):
        self._pressPos = self._style.GetInteractor().GetEventPosition()

        # The style does not run its own handler if observer is registered
        self._style.OnLeftButtonDown()

    def _leftButtonReleaseEvent(self, obj, event):
        x, y = self._style.GetInteractor().GetEventPosition()

        if (x, y) == self._pressPos:
            picker = vtkPropPicker()
            picker.PickProp(x, y, self._renderer)
            actor = picker.GetActor()
            self.actorPicked.emit(actor)

        # The style does not run its own handler if observer is registered
        self._style.OnLeftButtonUp()

    def _mouseWheelForwardEvent(self, obj, event):
        # The style does not run its own handler if observer is registered
        self._style.OnMouseWheelForward()

        self._resizeOriginAxis()
        self._widget.Render()

    def _mouseWheelBackwardEvent(self, obj, event):
        # The style does not run its own handler if observer is registered
        self._style.OnMouseWheelBackward()

        self._resizeOriginAxis()
        self._widget.Render()

    # This is a true observer calling.
    # No need to call style's method
    def _interactionEvent(self, obj, event):
        self._resizeOriginAxis()
        self._widget.Render()
