#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from os import path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QFileDialog

from view.widgets.number_input_dialog import PiecewiseLinearDialog, PolynomialDialog
from .temperature_widget_ui import Ui_temperatureWidget


class ProfileType(Enum):
    CONSTANT = 0
    SPATIAL_DISTRIBUTION = auto()
    TEMPORAL_DISTRIBUTION = auto()


class TemperatureWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self._ui = Ui_temperatureWidget()

        self._parent = parent

        self._ui.setupUi(self)
        self._connectSignalsSlots()

        self._profileTypeChanged(0)
        self._temporalDistributionTypeChanged()

    def _connectSignalsSlots(self):
        self._ui.profileType.currentIndexChanged.connect(self._profileTypeChanged)
        self._ui.spatialDistributionFileSelect.clicked.connect(self._selectSpatialDistributionFile)
        self._ui.temporalDistributionType.buttonClicked.connect(self._temporalDistributionTypeChanged)
        self._ui.peicewiseLinearEdit.clicked.connect(self._editPeicewiseLinear)
        self._ui.polynomialEdit.clicked.connect(self._editPolynomial)

    def _profileTypeChanged(self, index):
        self._ui.constant.setVisible(
            index == ProfileType.CONSTANT.value)
        self._ui.spatialDistribution.setVisible(
            index == ProfileType.SPATIAL_DISTRIBUTION.value)
        self._ui.temporalDistribution.setVisible(
            index == ProfileType.TEMPORAL_DISTRIBUTION.value)

        QTimer.singleShot(0, lambda: self._parent.adjustSize())

    def _selectSpatialDistributionFile(self):
        fileName = QFileDialog.getOpenFileName(self, self.tr("Open CSV File"), "", self.tr("CSV (*.csv)"))
        if fileName[0]:
            self._ui.spatialDistributionFileName.setText(path.basename(fileName[0]))

    def _temporalDistributionTypeChanged(self):
        self._ui.peicewiseLinearEdit.setEnabled(self._ui.peicewiseLinear.isChecked())
        self._ui.polynomialEdit.setEnabled(self._ui.polynomial.isChecked())

    def _editPeicewiseLinear(self):
        dialog = PiecewiseLinearDialog(self.tr("Temporal Distribution"), [self.tr("t"), self.tr("T")])
        dialog.exec()

    def _editPolynomial(self):
        dialog = PolynomialDialog(self.tr("Temporal Distribution"), "a")
        dialog.exec()
