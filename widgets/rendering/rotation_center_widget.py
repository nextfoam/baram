#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal
from vtkmodules.vtkCommonCore import vtkMath
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersSources import vtkSphereSource, vtkLineSource
from vtkmodules.vtkRenderingCore import vtkPropPicker, vtkActor, vtkDataSetMapper, vtkPolyDataMapper

from widgets.rendering.rendering_widget import MouseHandler, RenderingWidget


class RotationMouseHandler(MouseHandler):
    centerChanged = Signal(list)

    def __init__(self, view: RenderingWidget):
        super().__init__(view.interactor().GetInteractorStyle())

        self._view = view
        self._renderer = view.renderer()
        self._camera = self._renderer.GetActiveCamera()

        self._center = self._camera.GetFocalPoint()

    def center(self):
        return self._center

    def _leftButtonClicked(self, x, y):
        picker = vtkPropPicker()
        picker.PickProp(x, y, self._renderer, self._renderer.GetActors())

        self._center = picker.GetPickPosition()
        self.centerChanged.emit(self._center)

    def _mouseMoved(self, x, y, px, py):
        if not self._pressed:
            return False

        dx = px - x
        dy = py - y

        transform = vtkTransform()

        scale = vtkMath.Norm(self._camera.GetPosition())
        if scale <= 0.0:
            scale = vtkMath.Norm(self._camera.GetFocalPoint())
        if scale <= 0.0:
            scale = 1.0

        temp = self._camera.GetFocalPoint()
        self._camera.SetFocalPoint(temp[0] / scale, temp[1] / scale, temp[2] / scale)
        temp = self._camera.GetPosition()
        self._camera.SetPosition(temp[0] / scale, temp[1] / scale, temp[2] / scale)

        tx = self._center[0]
        ty = self._center[1]
        tz = self._center[2]

        transform.Identity()
        transform.Translate(tx / scale, ty / scale, tz / scale)

        self._camera.OrthogonalizeViewUp()
        size = self._renderer.GetSize()

        viewUp = self._camera.GetViewUp()
        transform.RotateWXYZ(360.0 * dx / size[0], viewUp[0], viewUp[1], viewUp[2])

        v2 = [0, 0, 0]
        vtkMath.Cross(self._camera.GetDirectionOfProjection(), viewUp, v2)
        transform.RotateWXYZ(-360.0 * dy / size[1], v2[0], v2[1], v2[2])

        transform.Translate(-tx / scale, -ty / scale, -tz / scale)

        self._camera.ApplyTransform(transform)
        self._camera.OrthogonalizeViewUp()

        temp = self._camera.GetFocalPoint()
        self._camera.SetFocalPoint(temp[0] * scale, temp[1] * scale, temp[2] * scale)
        temp = self._camera.GetPosition()
        self._camera.SetPosition(temp[0] * scale, temp[1] * scale, temp[2] * scale)

        self._view.refresh()

        return True


class RotationCenterActors:
    def __init__(self):
        self._lineX = vtkLineSource()
        self._lineY = vtkLineSource()
        self._lineZ = vtkLineSource()
        self._sphere = vtkSphereSource()

        self._actors = [vtkActor(), vtkActor(), vtkActor()]

        mapperX = vtkPolyDataMapper()
        mapperX.SetInputConnection(self._lineX.GetOutputPort())
        mapperY = vtkPolyDataMapper()
        mapperY.SetInputConnection(self._lineY.GetOutputPort())
        mapperZ = vtkPolyDataMapper()
        mapperZ.SetInputConnection(self._lineZ.GetOutputPort())
        mapper = vtkDataSetMapper()
        mapper.SetInputConnection(self._sphere.GetOutputPort())

        self._actors[0].SetMapper(mapperX)
        self._actors[1].SetMapper(mapperY)
        self._actors[2].SetMapper(mapperZ)
        # self._actors[3].SetMapper(mapper)

        for actor in self._actors:
            actor.GetProperty().SetColor(0.8, 0, 0)
            actor.GetProperty().SetLineWidth(2)

    def actors(self):
        return self._actors

    def setProperties(self, center, size):
        cx, cy, cz = center
        sx, sy, sz = size
        h = max(sx, sy, sz) / 20

        self._sphere.SetCenter(center)

        self._lineX.SetPoint1(cx - h, cy, cz)
        self._lineX.SetPoint2(cx + h, cy, cz)
        self._lineY.SetPoint1(cx, cy - h, cz)
        self._lineY.SetPoint2(cx, cy + h, cz)
        self._lineZ.SetPoint1(cx, cy, cz - h)
        self._lineZ.SetPoint2(cx, cy, cz + h)

        self._sphere.SetRadius(h / 3)
        self._sphere.SetPhiResolution(100)
        self._sphere.SetThetaResolution(100)


class RotationCenterWidget:
    def __init__(self, view: RenderingWidget):
        self._view = view
        self._mouseHandler = RotationMouseHandler(view)
        self._actors = RotationCenterActors()

        self._mouseHandler.centerChanged.connect(self._setCenter)

    def on(self):
        self._view.setMouseHandler(self._mouseHandler)
        self._showCenter()

    def off(self):
        self._view.resetMouseHandler()
        for actor in self._actors.actors():
            self._view.renderer().RemoveActor(actor)
        self._view.refresh()

    def _showCenter(self):
        for actor in self._actors.actors():
            self._view.renderer().AddActor(actor)

        self._setCenter(self._mouseHandler.center())

    def _setCenter(self, center):
        x1, x2, y1, y2, z1, z2 = self._view.getBounds()
        self._actors.setProperties(center, [x2 - x1, y2 - y1, z2 - z1])
        self._view.refresh()
