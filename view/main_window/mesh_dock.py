#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path

from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer
from vtkmodules.vtkIOGeometry import vtkOpenFOAMReader
from vtkmodules.vtkFiltersGeometry import vtkCompositeDataGeometryFilter
# load implementations for rendering and interaction factory classes
import vtkmodules.vtkRenderingOpenGL2
import vtkmodules.vtkInteractionStyle

from openfoam.file_system import FileSystem
from .tabified_dock import TabifiedDock


class MeshDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Mesh"))
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        # self._dockWidgetContents = QWidget()
        # self._layout = QVBoxLayout(self._dockWidgetContents)
        # self._layout.setContentsMargins(0, 0, 0, 0)
        self._widget = QVTKRenderWindowInteractor(self)
        self._renderer = vtkRenderer()
        self._widget.GetRenderWindow().AddRenderer(self._renderer)
        # self._layout.addWidget(self._widget)
        self.setWidget(self._widget)

        self._widget.Initialize()
        self._widget.Start()

    def showOpenFoamMesh(self):
        reader = vtkOpenFOAMReader()
        reader.SetFileName(FileSystem.foamFilePath())
        # reader.CreateCellToPointOn()
        # reader.DisableAllPointArrays()
        # reader.DecomposePolyhedraOn()
        reader.EnableAllPatchArrays()
        reader.Update()

        compositeFilter = vtkCompositeDataGeometryFilter()
        compositeFilter.SetInputConnection(reader.GetOutputPort())
        compositeFilter.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(compositeFilter.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)

        self._renderer.AddActor(actor)
        self._widget.Render()
