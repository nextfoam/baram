#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject
from superqt import QLabeledDoubleRangeSlider
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor

from baramMesh.app import app
from baramMesh.rendering.actor_info import MeshQualityIndex
from baramMesh.view.main_window.main_window_ui import Ui_MainWindow
from libbaram.colormap import sequentialRedLut
from widgets.rendering.rendering_widget import RenderingWidget


class MeshQualityInfo(QObject):
    def __init__(self, ui: Ui_MainWindow):
        super().__init__()

        self._widget = ui.meshQualityInfo
        self._header = ui.meshQualityHeader
        self._index = ui.meshQualityIndex
        self._slider = ui.meshQualityRangeSlider
        self._applyButton = ui.meshQualityApply
        self._view: RenderingWidget = ui.renderingView

        self._header.setContents(ui.meshQualityGroupBox)

        self._index.addItem('Aspect Ratio', MeshQualityIndex.ASPECT_RATIO)
        self._index.addItem('Non-orthogonal Angle', MeshQualityIndex.NON_ORTHO_ANGLE)
        self._index.addItem('Skewness', MeshQualityIndex.SKEWNESS)
        self._index.addItem('Volume', MeshQualityIndex.VOLUME)

        defaultIndex = self._index.findData(MeshQualityIndex.VOLUME)
        self._index.setCurrentIndex(defaultIndex)

        self._slider.setEdgeLabelMode(QLabeledDoubleRangeSlider.EdgeLabelMode.LabelIsRange)
        self._slider.setHandleLabelPosition(QLabeledDoubleRangeSlider.LabelPosition.LabelsAbove)
        self._slider.setRange(0, 100)
        self._slider.setValue((10, 20))

        self._legend = None

        self._connectSignalsSlots(ui)

    def isVisible(self):
        return self._widget.isVisible()

    def hide(self):
        self._widget.hide()
        self._clean()

    def show(self):
        self._header.setChecked(False)
        self._widget.show()

    def _connectSignalsSlots(self, ui):
        self._header.toggled.connect(self._toggled)
        self._index.currentIndexChanged.connect(self._meshQualityIndexChanged)
        self._applyButton.clicked.connect(self._apply)

    def _toggled(self, checked):
        if checked:
            self._index.setCurrentIndex(0)
        else:
            self._clean()

        self._view.refresh()

    def _meshQualityIndexChanged(self, index: int):
        qualityIndex: MeshQualityIndex = self._index.itemData(index)

        if app.window.meshManager:
            left, right = app.window.meshManager.getScalarRange(qualityIndex)

            # superqt Slider has an issue when left and right are same
            if left == right:
                if left == 0:  # (0, 0) defaults to (0, 1)
                    right = 1
                else:
                    left = left * 0.99  # 1% Reduction
                    right = right * 1.01  # 1% Addition

            # set slider range and interval
            self._slider.setRange(left, right)
            self._slider.setValue((left, right))

    def _apply(self):
        qualityIndex: MeshQualityIndex = self._index.currentData()

        if app.window.meshManager:
            app.window.meshManager.setScalar(qualityIndex)
            app.window.meshManager.setScalarBand(*self._slider.value())
            app.window.meshManager.applyCellFilter()

        if self._legend is None:
            self._legend = vtkScalarBarActor()
            self._legend.SetLookupTable(sequentialRedLut)
            self._legend.UnconstrainedFontSizeOn()
            self._legend.SetWidth(0.1)
            self._legend.SetHeight(0.4)
            self._legend.SetPosition(0.9, 0.03)
            self._view.addActor(self._legend)

        self._view.refresh()

    def _clean(self):
        if self._legend is not None:
            self._view.removeActor(self._legend)
            self._legend = None

        if app.window.meshManager:
            app.window.meshManager.clearCellFilter()

