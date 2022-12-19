#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal


if getattr(sys, 'frozen', False):
    APP_PATH = Path(sys.executable).parent.resolve()
else:
    APP_PATH = Path(__file__).parent.resolve()


class App(QObject):
    meshUpdated = Signal()

    def __init__(self):
        super().__init__()

        self._window = None
        self._vtkMesh = None
        self._closed = False

    @property
    def window(self):
        return self._window

    @property
    def meshDock(self):
        return self._window.meshDock()

    def vtkMesh(self):
        return self._vtkMesh

    def closed(self):
        return self._closed

    def setMainWindow(self, window):
        self._window = window
        self._closed = False

    def updateVtkMesh(self, mesh):
        self._vtkMesh = mesh
        self._vtkMesh.setToMesh()
        self.showVtkMesh()
        self._window.vtkMeshLoaded()
        self.meshUpdated.emit()

    def showVtkMesh(self):
        if self._vtkMesh:
            self._vtkMesh.activate()

    def close(self):
        self._closed = True


app = App()
