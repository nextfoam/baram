#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

APP_PATH = Path(__file__).parent.resolve()


class App:
    def __init__(self):
        self._window = None
        self._vtkMesh = None

    @property
    def window(self):
        return self._window

    def vtkMesh(self):
        return self._vtkMesh

    def setMainWindow(self, window):
        self._window = window

    @property
    def meshDock(self):
        return self._window.meshDock()

    def updateVtkMesh(self, mesh):
        self._vtkMesh = mesh
        mesh.activate()


app = App()
