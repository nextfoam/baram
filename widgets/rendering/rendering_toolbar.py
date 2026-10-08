#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog

from widgets.rendering.rendering_widget import RenderingWidget
from widgets.rendering.rotation_center_widget import RotationCenterWidget
from widgets.rendering.ruler_widget import RulerWidget
from widgets.themed_icon import load_themed_icon


class RenderingToolbar(QObject):
    background1Changed = Signal(QColor)
    background2Changed = Signal(QColor)

    def __init__(self, ui, view: RenderingWidget, dialogParent):
        super().__init__()

        self._ui = ui
        self._view = view
        self._dialogParent = dialogParent

        self._ruler = None
        self._rotationCenter = None
        self._dialog = None

        ui.axis.setIcon(load_themed_icon(':/graphicsIcons/originAxes'))
        ui.cubeAxis.setIcon(load_themed_icon(':/graphicsIcons/ruler.svg'))
        ui.ruler.setIcon(load_themed_icon(':/graphicsIcons/distance.svg'))
        ui.perspective.setIcon(load_themed_icon(':/graphicsIcons/2d-label-icon.svg'))
        ui.fit.setIcon(load_themed_icon(':/icons/expand.svg'))
        ui.alignAxis.setIcon(load_themed_icon(':/graphicsIcons/alignAxis.svg'))
        ui.rotate.setIcon(load_themed_icon(':/icons/reload.svg'))
        ui.rotationCenter.setIcon(load_themed_icon(':/graphicsIcons/rotationCenter'))

        self._updateBGButtonStyle(ui.bg1, QColor.fromRgbF(*view.background1()))
        self._updateBGButtonStyle(ui.bg2, QColor.fromRgbF(*view.background2()))

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        ui = self._ui
        view = self._view

        ui.axis.toggled.connect(view.setAxisVisible)
        ui.cubeAxis.toggled.connect(view.setCubeAxisVisible)
        ui.ruler.toggled.connect(self._setRulerVisible)
        ui.fit.clicked.connect(view.fitCamera)
        ui.perspective.toggled.connect(view.setParallelProjection)
        ui.alignAxis.clicked.connect(view.alignCamera)
        ui.rotate.clicked.connect(view.rollCamera)
        ui.rotationCenter.clicked.connect(self._toggleRotationCenter)
        ui.bg1.clicked.connect(self._pickBackground1)
        ui.bg2.clicked.connect(self._pickBackground2)

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
        dialog = QColorDialog(self._dialogParent)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setCustomColor(0, QColor(56, 61, 84))
        dialog.setCustomColor(1, QColor(209, 209, 209))

        return dialog

    def _setBackground1(self, color: QColor):
        self._view.setBackground1(color)
        self._updateBGButtonStyle(self._ui.bg1, color)
        self.background1Changed.emit(color)

    def _setBackground2(self, color: QColor):
        self._view.setBackground2(color)
        self._updateBGButtonStyle(self._ui.bg2, color)
        self.background2Changed.emit(color)

    def _updateBGButtonStyle(self, button, color: QColor):
        r, g, b, a = color.getRgb()
        button.setStyleSheet(
            f'background: rgb({r}, {g}, {b}); border-style: solid; border-color:black; border-width: 1')
