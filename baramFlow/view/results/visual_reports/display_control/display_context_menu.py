#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import QColorDialog, QMenu

from .display_item import ColorMode, DisplayMode, Properties
from .opacity_dialog import OpacityDialog


class DisplayContextMenu(QMenu):
    showActionTriggered = Signal()
    hideActionTriggered = Signal()
    opacitySelected = Signal(float)
    colorPicked = Signal(QColor)
    solidColorModeSelected = Signal()
    fieldColorModeSelected = Signal()

    wireframeDisplayModeSelected = Signal()
    surfaceDisplayModeSelected = Signal()
    surfaceEdgeDisplayModeSelected = Signal()

    vectorsToggled = Signal(bool)
    streamsToggled = Signal(bool)

    def __init__(self, parent):
        super().__init__(parent)

        self._opacityDialog = OpacityDialog(parent)
        self._colorDialog = QColorDialog(parent)
        self._colorDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._properties = None

        self._showAction: QAction = self.addAction(self.tr('Show'))
        self._showAction.triggered.connect(self.showActionTriggered)

        self._hideAction: QAction = self.addAction(self.tr('Hide'))
        self._hideAction.triggered.connect(self.hideActionTriggered)

        self._opacityAction: QAction = self.addAction(self.tr('Opacity'), self._openOpacityDialog)

        self._colorAction: QAction = self.addAction(self.tr('Color'), self._openColorDialog)

        self._colorModeMenu: QMenu = self.addMenu(self.tr('Color Mode'))

        self._solidColorAction: QAction = self._colorModeMenu.addAction(self.tr('Solid'), self._solidColorActionTriggered)
        self._solidColorAction.setCheckable(True)

        self._fieldColorAction: QAction = self._colorModeMenu.addAction(self.tr('Field'), self._fieldColorActionTriggered)
        self._fieldColorAction.setCheckable(True)

        self._displayModeMenu: QMenu = self.addMenu(self.tr('Display Mode'))

        self._wireFrameDisplayAction: QAction = self._displayModeMenu.addAction(self.tr('Wireframe'))
        self._wireFrameDisplayAction.triggered.connect(self.wireframeDisplayModeSelected)
        self._wireFrameDisplayAction.setCheckable(True)

        self._surfaceDisplayAction: QAction = self._displayModeMenu.addAction(self.tr('Surface'))
        self._surfaceDisplayAction.triggered.connect(self.surfaceDisplayModeSelected)
        self._surfaceDisplayAction.setCheckable(True)

        self._surfaceEdgeDisplayAction: QAction = self._displayModeMenu.addAction(self.tr('Surface with Edges'))
        self._surfaceEdgeDisplayAction.triggered.connect(self.surfaceEdgeDisplayModeSelected)
        self._surfaceEdgeDisplayAction.setCheckable(True)

        self.addSeparator()

        self._vectorsAction: QAction = self.addAction(self.tr('Show Vectors'))
        self._vectorsAction.toggled.connect(self._vectorsActionToggled)
        self._vectorsAction.setCheckable(True)

        self.addSeparator()

        self._streamsAction: QAction = self.addAction(self.tr('Show Streamlines'))
        self._streamsAction.toggled.connect(self._streamsActionToggled)
        self._streamsAction.setCheckable(True)

        self._connectSignalsSlots()

    def execute(self, pos, properties: Properties):
        self._properties = properties

        self._showAction.setVisible(not properties.visibility)
        self._hideAction.setVisible(properties.visibility is None or properties.visibility)
        self._solidColorAction.setChecked(properties.colorMode == ColorMode.SOLID)
        self._fieldColorAction.setChecked(properties.colorMode == ColorMode.FIELD)
        self._wireFrameDisplayAction.setChecked(properties.displayMode == DisplayMode.WIREFRAME)
        self._surfaceDisplayAction.setChecked(properties.displayMode == DisplayMode.SURFACE)
        self._surfaceEdgeDisplayAction.setChecked(properties.displayMode == DisplayMode.SURFACE_EDGE)

        if properties.showVectors is not None:
            self._vectorsAction.setVisible(True)
            self._vectorsAction.setChecked(properties.showVectors)

        if properties.showStreamlines is not None:
            self._streamsAction.setVisible(True)
            self._streamsAction.setChecked(properties.showStreamlines)

        self.exec(pos)

    def _connectSignalsSlots(self):
        self._opacityDialog.accepted.connect(lambda: self.opacitySelected.emit(self._opacityDialog.opacity()))
        self._colorDialog.accepted.connect(lambda: self.colorPicked.emit(self._colorDialog.selectedColor()))

    def _openOpacityDialog(self):
        self._opacityDialog.setOpacity(self._properties.opacity)
        self._opacityDialog.show()

    def _openColorDialog(self):
        self._colorDialog.setCurrentColor(
            Qt.GlobalColor.white if self._properties.color is None else self._properties.color)
        self._colorDialog.show()

    def _solidColorActionTriggered(self):
        self._colorAction.setEnabled(True)
        self.solidColorModeSelected.emit()

    def _fieldColorActionTriggered(self):
        self._colorAction.setEnabled(False)
        self.fieldColorModeSelected.emit()

    def _vectorsActionToggled(self, checked: bool):
        self.vectorsToggled.emit(checked)

    def _streamsActionToggled(self, checked: bool):
        self.streamsToggled.emit(checked)
