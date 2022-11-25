#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

APP_PATH = Path(__file__).parent.resolve()


class App:
    def __init__(self):
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
        mesh.activate()

    def close(self):
        self._closed = True


app = App()
