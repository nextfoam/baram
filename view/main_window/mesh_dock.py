#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from paraview.simple import CreateRenderView, OpenFOAMReader, Show, Render, RemoveViewsAndLayouts
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from .tabified_dock import TabifiedDock


class MeshDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderView = None

        self.setWindowTitle(self.tr("Mesh"))
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._dockWidgetContents = QWidget()
        self._layout = QVBoxLayout(self._dockWidgetContents)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._renderView = CreateRenderView()
        self._renderWidget = QVTKRenderWindowInteractor(
            rw=self._renderView.GetRenderWindow(), iren=self._renderView.GetInteractor())
        self._renderWidget.Initialize()

        self._layout.addWidget(self._renderWidget)
        self.setWidget(self._dockWidgetContents)

    def showMesh(self, fileName):
        RemoveViewsAndLayouts()
        self._layout.removeWidget(self._renderWidget)
        self._renderWidget.Finalize()

        self._renderView = CreateRenderView()
        self._renderWidget = QVTKRenderWindowInteractor(
            rw=self._renderView.GetRenderWindow(), iren=self._renderView.GetInteractor())
        self._renderWidget.Initialize()

        self._layout.addWidget(self._renderWidget)

        mesh = OpenFOAMReader(FileName=fileName)
        Show(mesh, self._renderView)
        Render()

    def closeEvent(self, event):
        self.hide()
        event.ignore()
