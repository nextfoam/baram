#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkInteractionWidgets import vtkPointWidget


class PointWidget(QObject):
    pointMoved = Signal(tuple)

    def __init__(self, view):
        super().__init__()

        self._view = view
        self._widget = vtkPointWidget()
        self._widget.SetInteractor(view.interactor())
        self._bounds = None

        self._widget.AddObserver('InteractionEvent', self._pointMoved)

    def setBounds(self, bounds):
        def center(a, b):
            return (a + b) / 2

        self._bounds = bounds
        position = center(bounds.xMin, bounds.xMax), center(bounds.yMin, bounds.yMax), center(bounds.zMin, bounds.zMax)
        self._widget.SetPosition(*position)
        self._widget.PlaceWidget(bounds.xMin, bounds.xMax, bounds.yMin, bounds.yMax, bounds.zMin, bounds.zMax)

        return position

    def setPosition(self, x, y, z):
        x = max(x, self._bounds.xMin)
        x = min(x, self._bounds.xMax)
        y = max(y, self._bounds.yMin)
        y = min(y, self._bounds.yMax)
        z = max(z, self._bounds.zMin)
        z = min(z, self._bounds.zMax)
        self._widget.SetPosition(x, y, z)

        return x, y, z

    def on(self):
        self._widget.On()

    def off(self):
        self._widget.Off()

    def close(self):
        self._widget.RemoveAllObservers()
        self._widget.Off()
        self._widget = None

    def _pointMoved(self, obj, evnent):
        self.pointMoved.emit(obj.GetPosition())
