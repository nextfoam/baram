#!/usr/bin/env python
# -*- coding: utf-8 -*-

# A simple script to demonstrate the vtkCutter function

import math
import platform
from enum import Enum, auto
from typing import Optional

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from PySide6.QtCore import QTimer, Qt, Signal, QObject
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget, QFileDialog, QVBoxLayout
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkCommand
# load implementations for rendering and interaction factory classes
from vtkmodules.vtkFiltersCore import vtkExtractCells
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkInteractionWidgets import vtkLogoRepresentation, vtkLogoWidget, vtkOrientationMarkerWidget
from vtkmodules.vtkIOImage import vtkPNGReader
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor, vtkCubeAxesActor
from vtkmodules.vtkRenderingCore import (
    vtkActor, vtkRenderer, vtkPropPicker, vtkCellPicker,
    vtkLightKit, vtkProp, vtkPolyDataMapper,
)

from libbaram.vtk_threads import isRenderingHold

from resources import resource


colors = vtkNamedColors()

RENDER_DELAY_TIME = 200
REPAINT_SUPPRESS_TIME = 100


class InteractionMode(Enum):
    NORMAL = auto()
    ROTATION_CENTER = auto()


class RenderWindowInteractor(QVTKRenderWindowInteractor):
    def __init__(self, parent=None, **kw):
        self._delayTimer = QTimer()
        self._delayTimer.setInterval(RENDER_DELAY_TIME)
        self._delayTimer.setSingleShot(True)
        self._delayTimer.timeout.connect(self._timeout)

        self._suppressTimer = QTimer()
        self._suppressTimer.setInterval(REPAINT_SUPPRESS_TIME)
        self._suppressTimer.setSingleShot(True)

        super().__init__(parent=parent, **kw)

    def Finalize(self):
        if self._RenderWindow is not None:
            self._RenderWindow.Finalize()
            self._RenderWindow = None

    def paintEvent(self, ev):
        if isRenderingHold():
            self._delayTimer.start()
            return

        if platform.system() == 'Darwin':
            if not self._suppressTimer.isActive():
                self._suppressTimer.start()
                super().paintEvent(ev)
        else:
            super().paintEvent(ev)

    def _timeout(self):
        self.Render()  # Render() just calls QWidget.update(), which just schedules repaint

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        ctrl, shift = self._GetCtrlShift(ev)

        x, y = ev.position().x(), ev.position().y()

        self._setEventInformation(x, y,
                                  ctrl, shift, chr(0), 0, None)

        if self._ActiveButton == Qt.MouseButton.LeftButton:
            self._Iren.InvokeEvent(vtkCommand.LeftButtonDoubleClickEvent, None)
        elif self._ActiveButton == Qt.MouseButton.RightButton:
            self._Iren.InvokeEvent(vtkCommand.RightButtonDoubleClickEvent, None)
        elif self._ActiveButton == Qt.MiddleButton:
            self._Iren.InvokeEvent(vtkCommand.MiddleButtonDoubleClickEvent, None)


class MouseHandler(QObject):
    mouseClicked = Signal(float, float, bool)
    cellSelectionRequested = Signal(float, float)

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
        if self._style.GetInteractor().GetShiftKey():
            self.cellSelectionRequested.emit(x, y)
        else:
            self.mouseClicked.emit(x, y, self._style.GetInteractor().GetControlKey())
        return False

    def _mouseMoved(self, x, y, px, py):
        return False


class RenderingWidget(QWidget):
    actorPicked = Signal(vtkActor, bool)
    viewClosed = Signal()

    cellSelected = Signal(object, int)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._dialog: Optional[QFileDialog] = None

        self._originAxes: Optional[vtkOrientationMarkerWidget] = None
        self._cubeAxesActor: Optional[vtkCubeAxesActor] = None

        self._actorPicker = vtkPropPicker()

        self._cellPicker = vtkCellPicker()
        self._cellPicker.SetTolerance(0.005)

        self._cellSelectionActor: Optional[vtkActor] = None

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

        self._defaultHandler = MouseHandler(self._style)
        self._handlers = {InteractionMode.NORMAL: self._defaultHandler}
        self._mode = InteractionMode.NORMAL
        self._activeHandler = self._defaultHandler

        self._wireHandlerSignals(self._defaultHandler)

        # To pick actors
        self._style.AddObserver(vtkCommand.LeftButtonPressEvent, self._leftButtonPressEvent)
        self._style.AddObserver(vtkCommand.LeftButtonReleaseEvent, self._leftButtonReleaseEvent)

        self._style.AddObserver(vtkCommand.MouseMoveEvent, self._mouseMoveEvent)

        # To adjust origin axes size on zoom
        # self._style.AddObserver(vtkCommand.MouseWheelForwardEvent, self._mouseWheelForwardEvent)
        # self._style.AddObserver(vtkCommand.MouseWheelBackwardEvent, self._mouseWheelBackwardEvent)
        # self._style.AddObserver(vtkCommand.InteractionEvent, self._interactionEvent)

    def interactor(self):
        return self._widget._Iren

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

    def pickCell(self, x, y):
        self._cellPicker.Pick(x, y, 0, self._renderer)
        actor = self._cellPicker.GetActor()
        cellId = self._cellPicker.GetCellId()
        return actor, cellId

    def showCellSelection(self, polyData, cellIds):
        self.clearCellSelection()

        if not cellIds:
            return

        from vtkmodules.vtkCommonCore import vtkIdList
        idList = vtkIdList()
        for cid in cellIds:
            idList.InsertNextId(cid)

        extractor = vtkExtractCells()
        extractor.SetInputData(polyData)
        extractor.SetCellList(idList)
        extractor.Update()

        geom = vtkGeometryFilter()
        geom.SetInputConnection(extractor.GetOutputPort())
        geom.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(geom.GetOutputPort())
        mapper.ScalarVisibilityOff()
        mapper.SetResolveCoincidentTopologyToPolygonOffset()
        mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(0.0, -1.0)

        self._cellSelectionActor = vtkActor()
        self._cellSelectionActor.SetMapper(mapper)
        prop = self._cellSelectionActor.GetProperty()
        prop.SetColor(1.0, 1.0, 1.0)
        prop.SetOpacity(1.0)
        prop.SetRepresentationToSurface()
        prop.EdgeVisibilityOn()
        prop.SetEdgeColor(1.0, 0.0, 1.0)
        prop.SetLineWidth(2.0)
        prop.SetLighting(False)

        self._renderer.AddActor(self._cellSelectionActor)
        self._widget.Render()

    def clearCellSelection(self):
        if self._cellSelectionActor is not None:
            self._renderer.RemoveActor(self._cellSelectionActor)
            self._cellSelectionActor = None
            self._widget.Render()

    def clear(self):
        self.clearCellSelection()
        self._renderer.RemoveAllViewProps()
        self._showLogo()

    def _turnCamera(self, orientation: tuple[float, float, float], up: tuple[float, float, float]):
        camera = self._renderer.GetActiveCamera()
        d = camera.GetDistance()
        fx, fy, fz = camera.GetFocalPoint()
        camera.SetPosition(fx-orientation[0]*d, fy-orientation[1]*d, fz-orientation[2]*d)
        camera.SetViewUp(up[0], up[1], up[2])

    def _getClosestAxis(self, u: tuple[float, float, float]) -> tuple[float, float, float]:
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

        # self._resizeOriginAxis()
        self._widget.Render()

    def setCubeAxisVisible(self, checked):
        if checked:
            self._showCubeAxes()
        else:
            self._hideCubeAxes()
        self._widget.Render()

    def getBounds(self):
        return self._renderer.ComputeVisiblePropBounds()

    def setBackground1(self, r, g, b):
        self._renderer.SetBackground(r, g, b)

    def setBackground2(self, r, g, b):
        self._renderer.SetBackground2(r, g, b)

    def background1(self):
        return self._renderer.GetBackground()

    def background2(self):
        return self._renderer.GetBackground2()

    def registerMouseHandler(self, mode: InteractionMode, handler):
        self._handlers[mode] = handler
        self._wireHandlerSignals(handler)

    def setInteractionMode(self, mode: InteractionMode):
        if mode == self._mode:
            return
        if mode not in self._handlers:
            raise ValueError(f'No handler registered for {mode}')
        self._mode = mode
        self._activeHandler = self._handlers[mode]

    def resetInteractionMode(self):
        self.setInteractionMode(InteractionMode.NORMAL)

    def interactionMode(self) -> InteractionMode:
        return self._mode

    def _wireHandlerSignals(self, handler):
        handler.mouseClicked.connect(self._mouseClicked)
        handler.cellSelectionRequested.connect(self._onCellSelectionRequested)

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
        if self._originAxes is None:
            self._originAxes = vtkOrientationMarkerWidget()
            self._originAxes.SetViewport(0.0, 0.0, 0.2, 0.2)
            self._originAxes.SetOrientationMarker(vtkAxesActor())
            self._originAxes.SetInteractor(self._widget)

        self._originAxes.EnabledOn()

    def _hideOriginAxes(self):
        if self._originAxes is not None:
            self._originAxes.EnabledOff()

    # def _resizeOriginAxis(self):
    #     if self._originActor:
    #         camera = self._renderer.GetActiveCamera()

    #         d = camera.GetDirectionOfProjection()
    #         p = camera.GetPosition()
    #         distance = abs(-p[0]*d[0]-p[1]*d[1]-p[2]*d[2])

    #         degree = camera.GetViewAngle()
    #         radian = math.radians(degree/3.0)
    #         length = distance * math.tan(radian)

    #         # length = self._style.getOriginActorLength()
    #         self._originActor.SetTotalLength(length, length, length)

    def _leftButtonPressEvent(self, obj, event):
        self._activeHandler.leftButtonPressed(obj, event)

    def _leftButtonReleaseEvent(self, obj, event):
        self._activeHandler.leftButtonReleased(obj, event)

    def rightButtonReleaseEvent(self):
        self._style.GetInteractor().InvokeEvent(vtkCommand.RightButtonReleaseEvent)

    def _mouseMoveEvent(self, obj, event):
        self._activeHandler.mouseMoved(obj, event)

    def _mouseClicked(self, x, y, controlKeyPressed):
        self.actorPicked.emit(self.pickActor(x, y), controlKeyPressed)

    # def _mouseWheelForwardEvent(self, obj, event):
    #     # The style does not run its own handler if observer is registered
    #     self._style.OnMouseWheelForward()

    #     self._resizeOriginAxis()
    #     self._widget.Render()

    # def _mouseWheelBackwardEvent(self, obj, event):
    #     # The style does not run its own handler if observer is registered
    #     self._style.OnMouseWheelBackward()

    #     self._resizeOriginAxis()
    #     self._widget.Render()

    # # This is a true observer calling.
    # # No need to call style's method
    # def _interactionEvent(self, obj, event):
    #     self._resizeOriginAxis()
    #     self._widget.Render()

    def _onCellSelectionRequested(self, x, y):
        actor, cellId = self.pickCell(x, y)
        self.cellSelected.emit(actor, cellId)

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
