#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog

from widgets.rendering.rendering_widget import RenderingWidget
from widgets.rendering.rotation_center_widget import RotationCenterWidget
from widgets.rendering.ruler_widget import RulerWidget

from baramMesh.app import app
from baramMesh.view.main_window.main_window_ui import Ui_MainWindow


class RenderingTool:
    def __init__(self, ui: Ui_MainWindow):
        self._ui = ui
        self._view: RenderingWidget = ui.renderingView

        self._ruler = None
        self._rotationCenter = None

        self._updateBGButtonStyle(self._ui.bg1, QColor.fromRgbF(*self._view.background1()))
        self._updateBGButtonStyle(self._ui.bg2, QColor.fromRgbF(*self._view.background2()))

        self._ui.alignAxis.clicked.connect(self._view.alignCamera)
        self._ui.axis.toggled.connect(self._view.setAxisVisible)
        self._ui.cubeAxis.toggled.connect(self._view.setCubeAxisVisible)
        self._ui.ruler.toggled.connect(self._setRulerVisible)
        self._ui.fit.clicked.connect(self._view.fitCamera)
        self._ui.perspective.toggled.connect(self._view.setParallelProjection)
        self._ui.rotate.clicked.connect(self._view.rollCamera)
        self._ui.rotationCenter.clicked.connect(self._toggleRotationCenter)
        self._ui.bg1.clicked.connect(self._pickBackground1)
        self._ui.bg2.clicked.connect(self._pickBackground2)

    def enable(self):
        self._ui.toolbar.setEnabled(True)
        self._ui.renderingView.setEnabled(True)

    def disable(self):
        self.clear()
        self._ui.toolbar.setEnabled(False)
        self._ui.renderingView.setEnabled(False)

    def clear(self):
        self._ui.axis.setChecked(False)
        self._ui.cubeAxis.setChecked(False)

    def _setRulerVisible(self, checked):
        if checked:
            self._ruler = RulerWidget(self._view.interactor(), self._view.renderer())
            self._ruler.on()
        else:
            self._ruler.off()
            self._ruler = None

    def _toggleRotationCenter(self, checked):
        if checked:
            self._rotationCenter = self._rotationCenter or RotationCenterWidget(self._view)
            self._rotationCenter.on()
        else:
            self._rotationCenter.off()

    def _pickBackground1(self):
        self._dialog = self._newBGColorDialog()
        self._dialog.colorSelected.connect(self._setBackground1)
        self._dialog.open()

    def _pickBackground2(self):
        self._dialog = self._newBGColorDialog()
        self._dialog.colorSelected.connect(self._setBackground2)
        self._dialog.open()

    def _newBGColorDialog(self):
        dialog = QColorDialog(app.window)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setCustomColor(0, QColor(56, 61, 84))
        dialog.setCustomColor(1, QColor(209, 209, 209))

        return dialog

    def _setBackground1(self, color):
        r, g, b, a = color.getRgbF()
        self._view.setBackground1(r, g, b)
        self._updateBGButtonStyle(self._ui.bg1, color)

    def _setBackground2(self, color):
        r, g, b, a = color.getRgbF()
        self._view.setBackground2(r, g, b)
        self._updateBGButtonStyle(self._ui.bg2, color)

    def _updateBGButtonStyle(self, button, color):
        r, g, b, a = color.getRgb()
        button.setStyleSheet(
            f'background: rgb({r}, {g}, {b}) border-style: solid border-color:black border-width: 1')
