#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform
import subprocess
from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QFileDialog
from vtkmodules.vtkRenderingCore import vtkActor

from baram.coredb.project import Project
from baram.coredb.app_settings import AppSettings
from baram.openfoam.file_system import FileSystem
from .rendering_view_ui import Ui_RenderingView


class DisplayMode(Enum):
    DISPLAY_MODE_FEATURE        = 0
    DISPLAY_MODE_POINTS         = auto()
    DISPLAY_MODE_SURFACE        = auto()
    DISPLAY_MODE_SURFACE_EDGE   = auto()
    DISPLAY_MODE_WIREFRAME      = auto()


class RenderingView(QWidget):
    actorPicked = Signal(vtkActor, bool)
    renderingModeChanged = Signal(DisplayMode)
    viewClosed = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._ui = Ui_RenderingView()
        self._ui.setupUi(self)

        self._view = self._ui.view

        for mode in DisplayMode:
            self._ui.renderingMode.setItemData(mode.value, mode)

        self._connectSignalsSlots()

    def renderingMode(self):
        return self._ui.renderingMode.currentData()

    def addActor(self, actor: vtkActor):
        self._view.addActor(actor)

    def removeActor(self, actor):
        self._view.removeActor(actor)

    def refresh(self):
        self._view.refresh()

    def fitCamera(self):
        self._view.fitCamera()

    def _connectSignalsSlots(self):
        self._ui.paraview.clicked.connect(self._runParaview)
        self._ui.axis.toggled.connect(self._view.setAxisVisible)
        self._ui.cubeAxis.toggled.connect(self._view.setCubeAxisVisible)
        self._ui.fit.clicked.connect(self._view.fitCamera)
        self._ui.perspective.toggled.connect(self._view.setParallelProjection)
        self._ui.alignAxis.clicked.connect(self._view.alignCamera)
        self._ui.rotate.clicked.connect(self._view.rollCamera)
        self._ui.renderingMode.currentIndexChanged.connect(self._renderingModeChanged)

        self._view.actorPicked.connect(self.actorPicked)
        self._view.viewClosed.connect(self.viewClosed)

    def _runParaview(self):
        casePath = ''
        if Project.instance().meshLoaded:
            casePath = FileSystem.foamFilePath()

        if platform.system() == 'Windows':
            # AppSettings has the paraview path.
            if path := AppSettings.getParaviewInstalledPath():
                if Path(path).exists():
                    subprocess.Popen([path, casePath])
                    return

            # Search the unique paraview executable file.
            paraviewHomes = list(Path('C:/Program Files').glob('paraview*'))
            if len(paraviewHomes) == 1:
                path = paraviewHomes[0] / 'bin/paraview.exe'
                if path.exists():
                    AppSettings.updateParaviewInstalledPath(path)
                    subprocess.Popen([path, casePath])
                    return

            # The system has no paraview executables or more than one.
            self._dialog = QFileDialog(self, self.tr('Select Paraview Program'), 'C:/Program Files', 'exe (*.exe)')
            self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
            self._dialog.fileSelected.connect(self._paraviewFileSelected)
            self._dialog.open()
        else:
            subprocess.Popen(['paraview', casePath])

    def _paraviewFileSelected(self, file):
        casePath = FileSystem.foamFilePath()
        AppSettings.updateParaviewInstalledPath(file)
        subprocess.Popen([f'{file}', f'{casePath}'])

    def _renderingModeChanged(self, index):
        print(f'renderingModechanged to {DisplayMode(index)}')

        # self._widget.Render()
        self.renderingModeChanged.emit(DisplayMode(index))
