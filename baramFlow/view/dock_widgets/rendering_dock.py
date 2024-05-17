#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
from enum import Enum, auto

from PySide6.QtCore import Signal, QCoreApplication, QEvent
from PySide6.QtWidgets import QWidget
from PySide6QtAds import CDockWidget
from vtkmodules.vtkRenderingCore import vtkActor

from baramFlow.coredb.app_settings import AppSettings
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.view.dock_widgets.rendering_view_ui import Ui_RenderingView


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

    def view(self):
        return self._view

    def close(self):
        self._view.close()
        return super().close()

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
        self._ui.axis.toggled.connect(self._view.setAxisVisible)
        self._ui.cubeAxis.toggled.connect(self._view.setCubeAxisVisible)
        self._ui.fit.clicked.connect(self._view.fitCamera)
        self._ui.perspective.toggled.connect(self._view.setParallelProjection)
        self._ui.alignAxis.clicked.connect(self._view.alignCamera)
        self._ui.rotate.clicked.connect(self._view.rollCamera)
        self._ui.renderingMode.currentIndexChanged.connect(self._renderingModeChanged)

        self._view.actorPicked.connect(self.actorPicked)
        self._view.viewClosed.connect(self.viewClosed)

    def _paraviewFileSelected(self, file):
        casePath = FileSystem.foamFilePath()
        AppSettings.updateParaviewInstalledPath(file)
        subprocess.Popen([f'{file}', f'{casePath}'])

    def _renderingModeChanged(self, index):
        print(f'renderingModechanged to {DisplayMode(index)}')

        # self._widget.Render()
        self.renderingModeChanged.emit(DisplayMode(index))


class RenderingDock(CDockWidget):
    def __init__(self):
        super().__init__(self._title())

        self._widget = RenderingView()
        self.setWidget(self._widget)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.setWindowTitle(self._title())

        super().changeEvent(event)

    def _title(self):
        return QCoreApplication.translate('RenderingDock', 'Mesh')
