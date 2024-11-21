#!/usr/bin/env python
# -*- coding: utf-8 -*-

# A simple script to demonstrate the vtkCutter function

import math
from typing import Optional

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QWidget, QFileDialog, QVBoxLayout
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkCommand
# load implementations for rendering and interaction factory classes
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkInteractionWidgets import vtkLogoRepresentation, vtkLogoWidget
from vtkmodules.vtkIOImage import vtkPNGReader
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor, vtkCubeAxesActor
from vtkmodules.vtkRenderingCore import vtkActor, vtkRenderer, vtkPropPicker, vtkLightKit, vtkProp

from resources import resource

# To fix middle button issue in vtkmodules
# Qt.MidButton that is not available in PySide6 is use in QVTKRenderWindowInteractor
# Remove this line when vtk 9.2.2 or later is used
Qt.MidButton = Qt.MiddleButton

colors = vtkNamedColors()


class RenderWindowInteractor(QVTKRenderWindowInteractor):
    def Finalize(self):
        if self._RenderWindow is not None:
            self._RenderWindow.Finalize()
            self._RenderWindow = None


class MouseHandler(QObject):
    mouseClicked = Signal(float, float, bool)

    def __init__(self, style):
        super().__init__()

        self._style = style
        self._pressPos = None
        self._pressed = False

    def leftButtonPressed(self, obj, event):
        self._pressed = True

        x, y = self._style.GetInteractor().GetEventPosition()
        self._pressPos = (x, y)

        handled = self._leftButtonPressed(x, y)

        # The style does not run its own handler if observer is registered
        if not handled:
            self._style.OnLeftButtonDown()

    def leftButtonReleased(self, obj, event):
        self._pressed = False

        x, y = self._style.GetInteractor().GetEventPosition()

        handled = self._leftButtonReleased(x, y)

        # The style does not run its own handler if observer is registered
        if not handled:
            self._style.OnLeftButtonUp()

    def mouseMoved(self, obj, event):
        x, y = self._style.GetInteractor().GetEventPosition()
        px, py = self._style.GetInteractor().GetLastEventPosition()

        handled = self._mouseMoved(x, y, px, py)

        # The style does not run its own handler if observer is registered
        if not handled:
            self._style.OnMouseMove()

    def _leftButtonPressed(self, x, y):
        return False

    def _leftButtonReleased(self, x, y):
        if (x, y) == self._pressPos:
            self._leftButtonClicked(x, y)
        return False

    def _leftButtonClicked(self, x, y):
        self.mouseClicked.emit(x, y, self._style.GetInteractor().GetControlKey())
        return False

    def _mouseMoved(self, x, y, px, py):
        return False


class RenderingWidget(QWidget):
    actorPicked = Signal(vtkActor, bool)
    viewClosed = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._dialog: Optional[QFileDialog] = None

        self._originActor: Optional[vtkAxesActor] = None
        self._cubeAxesActor: Optional[vtkCubeAxesActor] = None

        self._actorPicker = vtkPropPicker()

        self._style = vtkInteractorStyleTrackballCamera()
        self._widget = RenderWindowInteractor(self)
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

        self._lightKit = vtkLightKit()
        self._lightKit.AddLightsToRenderer(self._renderer)

        self._logoWidget = vtkLogoWidget()
        self._showLogo()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._widget)

        self._originalMouseObserver = MouseHandler(self._style)
        self._mouseObserver = self._originalMouseObserver

        self._mouseObserver.mouseClicked.connect(self._mouseClicked)

        # To pick actors
        self._style.AddObserver(vtkCommand.LeftButtonPressEvent, self._leftButtonPressEvent)
        self._style.AddObserver(vtkCommand.LeftButtonReleaseEvent, self._leftButtonReleaseEvent)

        self._style.AddObserver(vtkCommand.MouseMoveEvent, self._mouseMoveEvent)

        # To adjust origin axes size on zoom
        self._style.AddObserver(vtkCommand.MouseWheelForwardEvent, self._mouseWheelForwardEvent)
        self._style.AddObserver(vtkCommand.MouseWheelBackwardEvent, self._mouseWheelBackwardEvent)
        self._style.AddObserver(vtkCommand.InteractionEvent, self._interactionEvent)

    def interactor(self):
        return self._widget

    def renderer(self):
        return self._renderer

    def addActor(self, actor: vtkProp):
        self._renderer.AddActor(actor)

    def removeActor(self, actor: vtkProp):
        self._renderer.RemoveActor(actor)

    def refresh(self):
        self._widget.Render()

    def fitCamera(self):
        cubeAxesOn = False
        if self._cubeAxesActor is not None:
            self._hideCubeAxes()
            cubeAxesOn = True

        self._renderer.ResetCamera()

        if cubeAxesOn:
            self._showCubeAxes()

        self._widget.Render()

    def close(self):
        self.viewClosed.emit()
        self._widget.close()

        return super().close()

    def pickActor(self, x, y):
        self._actorPicker.PickProp(x, y, self._renderer)
        actor = self._actorPicker.GetActor()

        return actor

    def clear(self):
        self._renderer.RemoveAllViewProps()

    def _turnCamera(self, orientation: (float, float, float), up: (float, float, float)):
        camera = self._renderer.GetActiveCamera()
        d = camera.GetDistance()
        fx, fy, fz = camera.GetFocalPoint()
        camera.SetPosition(fx-orientation[0]*d, fy-orientation[1]*d, fz-orientation[2]*d)
        camera.SetViewUp(up[0], up[1], up[2])

    def _getClosestAxis(self, u: (float, float, float)) -> (float, float, float):
        axis = [0, 0, 0]
        i = u.index(max(u, key=abs))
        v = 1 if u[i] > 0 else -1
        axis[i] = v
        return axis

    def alignCamera(self):
        camera = self._renderer.GetActiveCamera()

        orientation = camera.GetDirectionOfProjection()
        orientation = self._getClosestAxis(orientation)

        up = camera.GetViewUp()
        up = self._getClosestAxis(up)

        self._turnCamera(orientation, up)
        self._widget.Render()

    def rollCamera(self):
        self._renderer.GetActiveCamera().Roll(-90)
        self._widget.Render()

    def setParallelProjection(self, checked):
        if checked:
            self._renderer.GetActiveCamera().ParallelProjectionOn()
        else:
            self._renderer.GetActiveCamera().ParallelProjectionOff()
        self._widget.Render()

    def setAxisVisible(self, checked):
        if checked:
            self._showOriginAxes()
        else:
            self._hideOriginAxes()

        self._resizeOriginAxis()
        self._widget.Render()

    def setCubeAxisVisible(self, checked):
        if checked:
            self._showCubeAxes()
        else:
            self._hideCubeAxes()
        self._widget.Render()

    def getBounds(self):
        if self._originActor is not None:
            self._originActor.SetVisibility(False)

        bounds = self._renderer.ComputeVisiblePropBounds()

        if self._originActor is not None:
            self._originActor.SetVisibility(True)

        return bounds

    def setBackground1(self, r, g, b):
        self._renderer.SetBackground(r, g, b)

    def setBackground2(self, r, g, b):
        self._renderer.SetBackground2(r, g, b)

    def background1(self):
        return self._renderer.GetBackground()

    def background2(self):
        return self._renderer.GetBackground2()

    def setMouseHandler(self, observer):
        self._mouseObserver = observer

    def resetMouseHandler(self):
        self._mouseObserver = self._originalMouseObserver

    def _showCubeAxes(self):
        if self._cubeAxesActor is not None:
            return

        self._cubeAxesActor = vtkCubeAxesActor()
        self._cubeAxesActor.SetBounds(self.getBounds())
        self._cubeAxesActor.SetScreenSize(12)
        self._cubeAxesActor.SetCamera(self._renderer.GetActiveCamera())

        axisColors = (
            colors.GetColor3d("Red"),
            colors.GetColor3d("Lime"),
            colors.GetColor3d("Blue")
        )
        for i in range(3):
            self._cubeAxesActor.GetTitleTextProperty(i).SetColor(axisColors[i])
            self._cubeAxesActor.GetLabelTextProperty(i).SetColor(axisColors[i])

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
        self._originActor.UseBoundsOff()
        self._originActor.SetConeRadius(0.2)
        self._originActor.SetShaftTypeToLine()
        self._originActor.SetNormalizedShaftLength(0.9, 0.9, 0.9)
        self._originActor.SetNormalizedTipLength(0.1, 0.1, 0.1)
        self._originActor.SetNormalizedLabelPosition(1.0, 1.0, 1.0)

        actor = self._originActor.GetXAxisCaptionActor2D()
        actor.SetPosition2(0.25, 0.05)

        actor = self._originActor.GetYAxisCaptionActor2D()
        actor.SetPosition2(0.25, 0.05)

        actor = self._originActor.GetZAxisCaptionActor2D()
        actor.SetPosition2(0.25, 0.05)

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
            distance = abs(-p[0]*d[0]-p[1]*d[1]-p[2]*d[2])

            degree = camera.GetViewAngle()
            radian = math.radians(degree/3.0)
            length = distance * math.tan(radian)

            # length = self._style.getOriginActorLength()
            self._originActor.SetTotalLength(length, length, length)

    def _leftButtonPressEvent(self, obj, event):
        self._mouseObserver.leftButtonPressed(obj, event)

    def _leftButtonReleaseEvent(self, obj, event):
        self._mouseObserver.leftButtonReleased(obj, event)

    def _mouseMoveEvent(self, obj, event):
        self._mouseObserver.mouseMoved(obj, event)

    def _mouseClicked(self, x, y, controlKeyPressed):
        self.actorPicked.emit(self.pickActor(x, y), controlKeyPressed)

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

    def _showLogo(self):
        reader = vtkPNGReader()
        reader.SetFileName(resource.file('nextfoam_eng.png'))
        reader.Update()

        logoRepresentation = vtkLogoRepresentation()
        logoRepresentation.SetImage(reader.GetOutput())
        logoRepresentation.SetPosition(0.9, 0)
        logoRepresentation.SetPosition2(0.1, 0.05)
        logoRepresentation.GetImageProperty().SetOpacity(0.7)

        self._logoWidget.SetInteractor(self._widget)
        self._logoWidget.SetRepresentation(logoRepresentation)
        self._logoWidget.ProcessEventsOff()

        self.refresh()
        self._logoWidget.On()

        self.refresh()
