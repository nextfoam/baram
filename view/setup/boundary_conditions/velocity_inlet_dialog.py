#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from os import path

from PySide6.QtWidgets import QFileDialog

from view.widgets.resizable_dialog import ResizableDialog
from view.widgets.polynomial_dialog import PiecewiseLinearDialog
from .velocity_inlet_dialog_ui import Ui_VelocityInletDialog
from .turbulence_model import TurbulenceModel
from .temperature_widget import TemperatureWidget


class VelocityInletDialog(ResizableDialog):
    class VELOCITY_SPECIFICATION_METHOD(Enum):
        COMPONENT = 0
        MAGNITUDE = auto()

    class PROFILE_TYPE(Enum):
        CONSTANT = 0
        SPATIAL_DISTRIBUTION = auto()
        TEMPORAL_DISTRIBUTION = auto()

    def __init__(self):
        super().__init__()
        self._ui = Ui_VelocityInletDialog()
        self._ui.setupUi(self)

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        self._temperatureWidget = TemperatureWidget(self)

        self._setup()
        self._connectSignalsSlots()

        self._profileTypeChagned()

    def _setup(self):
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)
        layout.addWidget(self._temperatureWidget)

    def _connectSignalsSlots(self):
        self._ui.velocitySpecificationMethod.currentIndexChanged.connect(self._velocitySpecificationMethodChanged)
        self._ui.profileType.currentIndexChanged.connect(self._profileTypeChagned)
        self._ui.spatialDistributionFileSelect.clicked.connect(self._selectSpatialDistributionFile)
        self._ui.temporalDistributionEdit.clicked.connect(self._editTemporalDistribution)

    def _velocitySpecificationMethodChanged(self):
        if self._ui.profileType.currentIndex() == self.PROFILE_TYPE.CONSTANT.value:
            self._profileTypeChagned()

    def _profileTypeChagned(self):
        self._ui.componentConstant.setVisible(
            self._ui.velocitySpecificationMethod.currentIndex() == self.VELOCITY_SPECIFICATION_METHOD.COMPONENT.value
            and self._ui.profileType.currentIndex() == self.PROFILE_TYPE.CONSTANT.value
        )
        self._ui.magnitudeConsant.setVisible(
            self._ui.velocitySpecificationMethod.currentIndex() == self.VELOCITY_SPECIFICATION_METHOD.MAGNITUDE.value
            and self._ui.profileType.currentIndex() == self.PROFILE_TYPE.CONSTANT.value
        )
        self._ui.spatialDistribution.setVisible(
            self._ui.profileType.currentIndex() == self.PROFILE_TYPE.SPATIAL_DISTRIBUTION.value
        )
        self._ui.temporalDistribution.setVisible(
            self._ui.profileType.currentIndex() == self.PROFILE_TYPE.TEMPORAL_DISTRIBUTION.value
        )

        self._resizeDialog(self._ui.velocity)

    def _selectSpatialDistributionFile(self):
        fileName = QFileDialog.getOpenFileName(self, self.tr("Open CSV File"), "", self.tr("CSV (*.csv)"))
        if fileName[0]:
            self._ui.spatialDistributionFileName.setText(path.basename(fileName[0]))

    def _editTemporalDistribution(self):
        if self._ui.velocitySpecificationMethod.currentIndex() == self.VELOCITY_SPECIFICATION_METHOD.COMPONENT.value:
            dialog = PiecewiseLinearDialog(self.tr("Temporal Distribution"),
                                           [self.tr("t"), self.tr("Ux"), self.tr("Uy"), self.tr("Uz")])
            dialog.exec()
        elif self._ui.velocitySpecificationMethod.currentIndex() == self.VELOCITY_SPECIFICATION_METHOD.MAGNITUDE.value:
            dialog = PiecewiseLinearDialog(self.tr("Temporal Distribution"), [self.tr("t"), self.tr("Umag")])
            dialog.exec()
