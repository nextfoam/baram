#!/usr/bin/env python
# -*- coding: utf-8 -*-

from vtkmodules.util.misc import calldata_type
from vtkmodules.vtkCommonCore import vtkCommand, VTK_INT
from vtkmodules.vtkInteractionWidgets import vtkDistanceWidget, vtkDistanceRepresentation
from vtkmodules.vtkRenderingCore import vtkPointPicker, vtkPropPicker, vtkRenderer


class RulerWidget:
    def __init__(self, interactor, renderer: vtkRenderer):
        self._widget = vtkDistanceWidget()
        self._renderer = renderer

        self._position1 = None
        self._position2 = None

        self._widget.SetInteractor(interactor)
        self._widget.CreateDefaultRepresentation()
        self._widget.AddObserver(vtkCommand.PlacePointEvent, self._pointCreated)
        self._widget.AddObserver(vtkCommand.InteractionEvent, self._pointMoved)
        self._widget.AddObserver(vtkCommand.EndInteractionEvent, self._pointMoved)

        self._representation: vtkDistanceRepresentation = self._widget.GetRepresentation()
        self._representation.SetLabelFormat('%6g')

    def on(self):
        self._widget.On()

    def off(self):
        self._widget.Off()

    @calldata_type(VTK_INT)
    def _pointCreated(self, obj, event, handleID):
        if handleID == 0:
            self._adjustPoint1()
        elif handleID == 1:
            self._adjustPoint2()

    def _pointMoved(self, obj, event):
        if self._position1 != self._representation.GetPoint1WorldPosition():  # point1 handle has moved
            self._adjustPoint1()

        if self._position2 != self._representation.GetPoint2WorldPosition():  # point2 handle has moved
            self._adjustPoint2()

    def _adjustPoint1(self):
        p = [0, 0, 0]  # position buffer
        self._representation.GetPoint1Representation().GetDisplayPosition(p)

        pos = self._pickActorPoint(p[0], p[1])
        if pos is not None:  # snap to actor
            self._representation.SetPoint1WorldPosition(pos)
            self._position1 = pos
        else:
            self._representation.GetPoint1WorldPosition(p)
            self._position1 = p

    def _adjustPoint2(self):
        p = [0, 0, 0]  # position buffer
        self._representation.GetPoint2Representation().GetDisplayPosition(p)

        pos = self._pickActorPoint(p[0], p[1])
        if pos is not None:  # snap to actor
            self._representation.SetPoint2WorldPosition(pos)
            self._position2 = pos
        else:
            self._representation.GetPoint2WorldPosition(p)
            self._position2 = p

    def _pickActorPoint(self, dpx, dpy):
        picker = vtkPropPicker()
        rv = picker.PickProp(dpx, dpy, self._renderer, self._renderer.GetActors())
        if rv == 0:  # No Prop picker
            return None

        return picker.GetPickPosition()
