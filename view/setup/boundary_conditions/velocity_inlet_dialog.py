#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from os import path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QDialog

from view.widgets.number_input_dialog import PiecewiseLinearDialog
from .velocity_inlet_dialog_ui import Ui_VelocityInletDialog
from .turbulence_model import TurbulenceModel
from .temperature_widget import TemperatureWidget


class VelocitySpecificationMethod(Enum):
    COMPONENT = 0
    MAGNITUDE = auto()


class ProfileType(Enum):
    CONSTANT = 0
    SPATIAL_DISTRIBUTION = auto()
    TEMPORAL_DISTRIBUTION = auto()


class VelocityInletDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_VelocityInletDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        self._temperatureWidget = TemperatureWidget(self)
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
        layout.addWidget(self._temperatureWidget)

        self._connectSignalsSlots()

        self._profileTypeChanged()

    def _connectSignalsSlots(self):
        self._ui.velocitySpecificationMethod.currentIndexChanged.connect(self._velocitySpecificationMethodChanged)
        self._ui.profileType.currentIndexChanged.connect(self._profileTypeChanged)
        self._ui.spatialDistributionFileSelect.clicked.connect(self._selectSpatialDistributionFile)
        self._ui.temporalDistributionEdit.clicked.connect(self._editTemporalDistribution)

    def _velocitySpecificationMethodChanged(self):
        if self._ui.profileType.currentIndex() == ProfileType.CONSTANT.value:
            self._profileTypeChanged()

    def _profileTypeChanged(self):
        self._ui.componentConstant.setVisible(
            self._ui.velocitySpecificationMethod.currentIndex() == VelocitySpecificationMethod.COMPONENT.value
            and self._ui.profileType.currentIndex() == ProfileType.CONSTANT.value
        )
        self._ui.magnitudeConsant.setVisible(
            self._ui.velocitySpecificationMethod.currentIndex() == VelocitySpecificationMethod.MAGNITUDE.value
            and self._ui.profileType.currentIndex() == ProfileType.CONSTANT.value
        )
        self._ui.spatialDistribution.setVisible(
            self._ui.profileType.currentIndex() == ProfileType.SPATIAL_DISTRIBUTION.value
        )
        self._ui.temporalDistribution.setVisible(
            self._ui.profileType.currentIndex() == ProfileType.TEMPORAL_DISTRIBUTION.value
        )

        QTimer.singleShot(0, lambda: self.adjustSize())

    def _selectSpatialDistributionFile(self):
        fileName = QFileDialog.getOpenFileName(self, self.tr("Open CSV File"), "", self.tr("CSV (*.csv)"))
        if fileName[0]:
            self._ui.spatialDistributionFileName.setText(path.basename(fileName[0]))

    def _editTemporalDistribution(self):
        if self._ui.velocitySpecificationMethod.currentIndex() == VelocitySpecificationMethod.COMPONENT.value:
            dialog = PiecewiseLinearDialog(self.tr("Temporal Distribution"),
                                           [self.tr("t"), self.tr("Ux"), self.tr("Uy"), self.tr("Uz")])
            dialog.exec()
        elif self._ui.velocitySpecificationMethod.currentIndex() == VelocitySpecificationMethod.MAGNITUDE.value:
            dialog = PiecewiseLinearDialog(self.tr("Temporal Distribution"), [self.tr("t"), self.tr("Umag")])
            dialog.exec()
