#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess

from baramFlow.coredb.app_settings import AppSettings
from baramFlow.mesh.mesh_model import DisplayMode
from baramFlow.openfoam.file_system import FileSystem
from widgets.rendering.rotation_center_widget import RotationCenterWidget
from widgets.rendering.ruler_widget import RulerWidget

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QWidget
from vtkmodules.vtkRenderingCore import vtkActor

from .rendering_view_ui import Ui_RenderingView


class RenderingView(QWidget):
    actorPicked = Signal(vtkActor, bool)
    renderingModeChanged = Signal(DisplayMode)
    viewClosed = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._ui = Ui_RenderingView()
        self._ui.setupUi(self)

        self._view = self._ui.view

        self._rotationCenter = None

        self._dialog = None

        self._updateBGButtonStyle(self._ui.bg1, QColor.fromRgbF(*self._view.background1()))
        self._updateBGButtonStyle(self._ui.bg2, QColor.fromRgbF(*self._view.background2()))

        for mode in DisplayMode:
            self._ui.renderingMode.setItemData(mode.value, mode)

        # Class name of "RenderingView" is used
        # not to call the method of my children
        # but to call my own method
        RenderingView._connectSignalsSlots(self)

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
        self._ui.ruler.toggled.connect(self._setRulerVisible)
        self._ui.fit.clicked.connect(self._view.fitCamera)
        self._ui.perspective.toggled.connect(self._view.setParallelProjection)
        self._ui.alignAxis.clicked.connect(self._view.alignCamera)
        self._ui.rotate.clicked.connect(self._view.rollCamera)
        self._ui.rotationCenter.clicked.connect(self._toggleRotationCenter)
        self._ui.renderingMode.currentIndexChanged.connect(self._renderingModeChanged)
        self._ui.bg1.clicked.connect(self._pickBackground1)
        self._ui.bg2.clicked.connect(self._pickBackground2)

        self._view.actorPicked.connect(self.actorPicked)
        self._view.viewClosed.connect(self.viewClosed)

    def _setRulerVisible(self, checked):
        if checked:
            self._ruler = RulerWidget(self._view.interactor(), self._view.renderer())
            self._ruler.on()
        else:
            self._ruler.off()
            self._ruler = None

    def _paraviewFileSelected(self, file):
        casePath = FileSystem.foamFilePath()
        AppSettings.updateParaviewInstalledPath(file)
        subprocess.Popen([f'{file}', f'{casePath}'])

    def _toggleRotationCenter(self, checked):
        if checked:
            self._rotationCenter = self._rotationCenter or RotationCenterWidget(self._view)
            self._rotationCenter.on()
        else:
            self._rotationCenter.off()

    def _renderingModeChanged(self, index):
        self.renderingModeChanged.emit(DisplayMode(index))

    def _pickBackground1(self):
        self._dialog = self._newBGColorDialog()
        self._dialog.colorSelected.connect(self._setBackground1)
        self._dialog.open()

    def _pickBackground2(self):
        self._dialog = self._newBGColorDialog()
        self._dialog.colorSelected.connect(self._setBackground2)
        self._dialog.open()

    def _newBGColorDialog(self):
        dialog = QColorDialog(self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setCustomColor(0, QColor(56, 61, 84))
        dialog.setCustomColor(1, QColor(209, 209, 209))

        return dialog

    def _setBackground1(self, color: QColor):
        r, g, b, a = color.getRgbF()
        self._view.setBackground1(r, g, b)
        self._updateBGButtonStyle(self._ui.bg1, color)

    def _setBackground2(self, color: QColor):
        r, g, b, a = color.getRgbF()
        self._view.setBackground2(r, g, b)
        self._updateBGButtonStyle(self._ui.bg2, color)

    def _updateBGButtonStyle(self, button, color: QColor):
        r, g, b, a = color.getRgb()
        button.setStyleSheet(
            f'background: rgb({r}, {g}, {b}); border-style: solid; border-color:black; border-width: 1')