#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import QDialog, QTreeWidgetItem, QLabel, QTreeWidget, QWidget, QHBoxLayout, QHeaderView
from PySide6.QtGui import QColor, QDoubleValidator, QIntValidator

from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

from baramMesh.view.geometry.split_dialog_ui import Ui_SplitDialog
from baramMesh.view.geometry.stl_utility import StlImporter

from libbaram.colormap import getLookupTable


class SegmentItem(QTreeWidgetItem):
    def __init__(self, parent: QTreeWidget, sid: int, color: QColor, area: float):
        super().__init__(parent, [str(sid), None, f'{area:.3g}'])

        self._colorWidget = QLabel()

        self._colorWidget.setStyleSheet(
            f'background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border: 1px solid LightGrey; border-radius: 3px;')

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(9, 1, 9, 1)
        layout.addWidget(self._colorWidget)

        self._colorWidget.setMinimumSize(16, 16)
        parent.setItemWidget(self, 1, widget)


class SplitDialog(QDialog):
    def __init__(self, parent, files: [Path], angle):
        super().__init__(parent)

        self._ui = Ui_SplitDialog()
        self._ui.setupUi(self)

        self._view = self._ui.renderingView

        self._future: Optional[asyncio.Future] = None

        self._stlImporter = StlImporter()

        self._ui.featureAngleSlider.setValue(angle)
        self._ui.featureAngleText.setValidator(QIntValidator(0, 180))
        self._ui.featureAngleText.setText(str(angle))

        self._ui.minAreaSlider.setRange(0, 100)
        self._ui.minAreaText.setValidator(QDoubleValidator(0, 100, -1))

        self._ui.segments.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._ui.segments.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._ui.segments.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self._edgeMapper = vtkPolyDataMapper()
        self._edgeMapper.ScalarVisibilityOff()

        self._edgeActor = vtkActor()
        self._edgeActor.SetMapper(self._edgeMapper)
        self._edgeActor.GetProperty().SetColor(vtkNamedColors().GetColor3d('White'))
        self._edgeActor.GetProperty().SetLineWidth(2.0)

        self._view.addActor(self._edgeActor)

        self._regionMapper = vtkPolyDataMapper()
        self._regionMapper.ScalarVisibilityOn()
        self._regionMapper.SelectColorArray('RegionId')
        self._regionMapper.SetScalarModeToUseCellData()
        self._regionMapper.SetColorModeToMapScalars()
        lut = getLookupTable('rainbow')
        self._regionMapper.SetLookupTable(lut)

        self._regionActor = vtkActor()
        self._regionActor.SetMapper(self._regionMapper)
        self._regionActor.GetProperty().SetOpacity(1)
        self._regionActor.GetProperty().SetRepresentationToSurface()
        self._regionActor.GetProperty().EdgeVisibilityOff()

        self._view.addActor(self._regionActor)

        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._stlImporter.load(files)

        self._apply()

        self._view.fitCamera()

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.featureAngleSlider.valueChanged.connect(self._featureAngleSliderChanged)
        self._ui.featureAngleText.editingFinished.connect(self._featureAngleTextEditingFinished)

        self._ui.minAreaSlider.valueChanged.connect(self._minAreaSliderChanged)
        self._ui.minAreaText.editingFinished.connect(self._minAreaTextEditingFinished)

        self._ui.apply.clicked.connect(self._apply)

        self._ui.alignAxis.clicked.connect(self._view.alignCamera)
        self._ui.axis.toggled.connect(self._view.setAxisVisible)
        self._ui.cubeAxis.toggled.connect(self._view.setCubeAxisVisible)
        self._ui.fit.clicked.connect(self._view.fitCamera)
        self._ui.perspective.toggled.connect(self._view.setParallelProjection)
        self._ui.rotate.clicked.connect(self._view.rollCamera)

        self._ui.okButton.clicked.connect(self._okClicked)
        self._ui.cancelButton.clicked.connect(self._cancelClicked)

    def _featureAngleSliderChanged(self, value):
        self._ui.featureAngleText.setText(str(value))

    def _featureAngleTextEditingFinished(self):
        angle = int(self._ui.featureAngleText.text())
        self._ui.featureAngleSlider.setValue(angle)

    def _minAreaSliderChanged(self, value):
        self._ui.minAreaText.setText(f'{value:.3g}')

    def _minAreaTextEditingFinished(self):
        minArea = float(self._ui.minAreaText.text())

        with QSignalBlocker(self._ui.minAreaSlider):
            self._ui.minAreaSlider.setValue(minArea)

    def _apply(self):
        angle = float(self._ui.featureAngleText.text())
        minArea = float(self._ui.minAreaText.text()) / 100

        segments, regionedData, edges = self._stlImporter.split(angle, minArea)

        self._edgeMapper.RemoveAllInputs()
        self._edgeMapper.SetInputData(edges)
        self._edgeMapper.Update()

        self._regionMapper.RemoveAllInputs()
        self._regionMapper.SetInputData(regionedData)
        self._regionMapper.SetScalarRange(0, len(segments)-1)
        self._regionMapper.Update()

        self._ui.numSegments.setText(f'{len(segments) :,}')

        self._ui.segments.clear()
        self._view.refresh()

        for i in range(0, len(segments)):
            SegmentItem(self._ui.segments, i, self._getColor(i), segments[i][1])

        self._view.refresh()

    def _getColor(self, value):
        minValue, maxValue = self._regionMapper.GetScalarRange()
        lut: vtkLookupTable = self._regionMapper.GetLookupTable()
        lut.SetRange(minValue, maxValue)

        rgb = [0, 0, 0]
        if value < minValue:
            value = minValue
        elif value > maxValue:
            value = maxValue

        lut.GetColor(value, rgb)

        return QColor.fromRgbF(rgb[0], rgb[1], rgb[2])

    def show(self) -> asyncio.Future:
        loop = asyncio.get_running_loop()
        self._future = loop.create_future()

        super().show()

        return self._future

    def _okClicked(self):
        if not self._future.done():
            volumes, surfaces = self._stlImporter.identifyVolumes()
            self._future.set_result((volumes, surfaces))

        self.close()

    def _cancelClicked(self):
        if not self._future.cancelled():
            self._future.cancel()

        self.close()

    def closeEvent(self, event):
        if not self._future.done():
            self._future.cancel()

        self._view.close()

        event.accept()
