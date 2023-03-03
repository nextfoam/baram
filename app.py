#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTranslator, QCoreApplication, QLocale

from resources import resource


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
        self._translator = None

    @property
    def window(self):
        return self._window

    @property
    def renderingView(self):
        return self._window.renderingView()

    def vtkMesh(self):
        return self._vtkMesh

    def closed(self):
        return self._closed

    def setMainWindow(self, window):
        self._window = window
        self._closed = False

    def updateVtkMesh(self, mesh):
        if self._vtkMesh:
            self._vtkMesh.deactivate()

        self._vtkMesh = mesh
        self._window.vtkMeshLoaded()
        self.meshUpdated.emit()
        self.showMesh()

    def showMesh(self):
        self._vtkMesh.activate()

    def close(self):
        self._closed = True

    def setLanguage(self, language):
        QCoreApplication.removeTranslator(self._translator)
        self._translator = QTranslator()
        self._translator.load(QLocale(QLocale.languageToCode(QLocale(language).language())),
                              'baram', '_', str(resource.file('locale')))
        QCoreApplication.installTranslator(self._translator)


app = App()
