#!/usr/bin/env python
# -*- coding: utf-8 -*-

from vtkmodules.util.misc import calldata_type
from vtkmodules.vtkCommonCore import vtkCommand, VTK_INT
from vtkmodules.vtkInteractionWidgets import vtkDistanceWidget
from vtkmodules.vtkRenderingCore import vtkPointPicker, vtkPropPicker


class RulerWidget:
    def __init__(self, interactor, renderer):
        self._widget = vtkDistanceWidget()
        self._renderer = renderer

        self._position1 = None
        self._position2 = None

        self._pointPicker = vtkPointPicker()
        self._propPicker = vtkPropPicker()

        self._widget.SetInteractor(interactor)
        self._widget.CreateDefaultRepresentation()
        self._widget.AddObserver(vtkCommand.PlacePointEvent, self._pointCreated)
        self._widget.AddObserver(vtkCommand.EndInteractionEvent, self._pointMoved)

    def on(self):
        self._widget.On()

    def off(self):
        self._widget.Off()

    @calldata_type(VTK_INT)
    def _pointCreated(self, obj, event, handleID):
        if handleID == 0:
            self._position1 = self._adjustPoint(self._widget.GetRepresentation().GetPoint1Representation())
        elif handleID == 1:
            self._position2 = self._adjustPoint(self._widget.GetRepresentation().GetPoint2Representation())

    def _pointMoved(self, obj, event):
        self._position1 = self._adjustPoint(self._widget.GetRepresentation().GetPoint1Representation(), self._position1)
        self._position2 = self._adjustPoint(self._widget.GetRepresentation().GetPoint2Representation(), self._position2)
    #
    # def _adjustPoint(self, representation, oldPosition=None):
    #     p = [0, 0, 0]
    #     representation.GetWorldPosition(p)
    #     if p == oldPosition:
    #         return
    #
    #     representation.GetDisplayPosition(p)
    #     self._pointPicker.Pick(p, self._renderer)
    #     pos = self._pointPicker.GetPickPosition()
    #     representation.SetWorldPosition(pos)
    #
    #     return pos

    def _adjustPoint(self, representation, oldPosition=None):
        p = [0, 0, 0]
        representation.GetWorldPosition(p)
        if p == oldPosition:
            return oldPosition

        representation.GetDisplayPosition(p)
        self._propPicker.PickProp(p[0], p[1], self._renderer)
        pos = self._propPicker.GetPickPosition()
        representation.SetWorldPosition(pos)

        representation.GetWorldPosition(p)
        return p
