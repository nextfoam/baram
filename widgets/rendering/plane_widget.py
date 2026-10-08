#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonDataModel import vtkPlane
from vtkmodules.vtkInteractionWidgets import vtkImplicitPlaneWidget2, vtkImplicitPlaneRepresentation
from vtkmodules.vtkCommonCore import vtkCommand


class PlaneWidget(QObject):
    planeMoved = Signal(tuple)

    def __init__(self, view):
        super().__init__()

        self._view = view
        self._widget = vtkImplicitPlaneWidget2()
        self._plane = vtkPlane()

        rep = vtkImplicitPlaneRepresentation()
        rep.SetPlaceFactor(1.25)  # This must be set prior to placing the widget
        rep.OutlineTranslationOff()
        rep.GetNormalProperty().SetOpacity(0)
        rep.GetSelectedNormalProperty().SetOpacity(0)

        self._widget.SetInteractor(view.interactor())
        self._widget.SetRepresentation(rep)

        self._widget.AddObserver(vtkCommand.InteractionEvent, self._planeMoved)

    def setOrigin(self, origin):
        self._widget.GetImplicitPlaneRepresentation().SetOrigin(*origin)
        self._view.refresh()

        return self.origin()

    def origin(self):
        origin = [0, 0, 0]
        self._widget.GetImplicitPlaneRepresentation().GetOrigin(origin)

        return origin

    def setBounds(self, bounds):
        self._widget.GetImplicitPlaneRepresentation().PlaceWidget(bounds.toTuple())

    def setNormal(self, normal):
        self._widget.GetImplicitPlaneRepresentation().SetNormal(*normal)
        self._view.refresh()

    def on(self, normal):
        self._widget.GetImplicitPlaneRepresentation().SetNormal(*normal)
        self._widget.On()

    def off(self):
        self._widget.Off()
        self._view.refresh()

    def isEnabled(self):
        return self._widget.GetEnabled()

    def close(self):
        self._widget.RemoveAllObservers()
        self._widget.Off()
        self._widget = None

    def _planeMoved(self, obj, evnent):
        self._widget.GetImplicitPlaneRepresentation().GetPlane(self._plane)
        self.planeMoved.emit(self._plane.GetOrigin())
