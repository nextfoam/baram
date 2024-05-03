#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QDoubleValidator, QIntValidator

from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

from baramMesh.view.geometry.split_dialog_ui import Ui_SplitDialog
from baramMesh.view.geometry.stl_utility import StlImporter

from widgets.turbo_colormap import turboLookupTable


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
        self._regionMapper.SetLookupTable(turboLookupTable)

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

        # To disconnect/connect o prevent infinite call loop
        self._ui.minAreaSlider.valueChanged.disconnect(self._minAreaSliderChanged)
        self._ui.minAreaSlider.setValue(minArea)
        self._ui.minAreaSlider.valueChanged.connect(self._minAreaSliderChanged)

    def _apply(self):
        angle = float(self._ui.featureAngleText.text())
        minArea = float(self._ui.minAreaText.text()) / 100

        numRegions, regionedData, edges = self._stlImporter.split(angle, minArea)

        self._ui.numSegments.setText(f'{numRegions :,}')

        self._edgeMapper.RemoveAllInputs()
        self._edgeMapper.SetInputData(edges)
        self._edgeMapper.Update()

        self._regionMapper.RemoveAllInputs()
        self._regionMapper.SetInputData(regionedData)
        self._regionMapper.SetScalarRange(0, numRegions)
        self._regionMapper.Update()

        self._view.refresh()

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
