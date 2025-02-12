#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from dataclasses import dataclass

from PySide6.QtGui import QColor
from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonDataModel import vtkDataObject, vtkPlane
from vtkmodules.vtkFiltersCore import vtkClipPolyData, vtkThreshold, vtkPassThrough, vtkCutter
from vtkmodules.vtkFiltersExtraction import vtkExtractPolyDataGeometry, vtkExtractGeometry
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkDataSetMapper, vtkActor, vtkMapper
from vtkmodules.vtkCommonColor import vtkNamedColors

from libbaram.mesh import Bounds
from libbaram.colormap import sequentialRedLut



class ActorType(Enum):
    GEOMETRY = auto()
    BOUNDARY = auto()
    MESH = auto()


class ActorInfo(QObject):
    sourceChanged = Signal(str)
    nameChanged = Signal(str)

    def id(self):
        return self._id

    def name(self):
        return self._name

    def type(self):
        return self._type

    def dataSet(self):
        return self._dataSet

    def actor(self):
        return self._actor

    def bounds(self):
        return Bounds(*self._dataSet.GetBounds())

    def isVisible(self):
        return self._properties.visibility

    def color(self):
        return self._properties.color

    def setName(self, name):
        self._name = name
        self.nameChanged.emit(name)

