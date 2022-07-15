#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from coredb import coredb
from coredb.filedb import FileDB, BcFileRole, FileFormatError
from coredb.coredb_writer import CoreDBWriter
from coredb.models_db import ModelsDB
from coredb.boundary_db import BoundaryDB, VelocitySpecification, VelocityProfile
from view.widgets.resizable_dialog import ResizableDialog
from view.widgets.number_input_dialog import PiecewiseLinearDialog
from .velocity_inlet_dialog_ui import Ui_VelocityInletDialog
from .turbulence_model_helper import TurbulenceModelHelper
from .temperature_widget import TemperatureWidget


class VelocityInletDialog(ResizableDialog):
    RELATIVE_XPATH = '/velocityInlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_VelocityInletDialog()
        self._ui.setupUi(self)

        self._bcid = bcid

        self._specifications = {
            VelocitySpecification.COMPONENT.value: self.tr("Component"),
            VelocitySpecification.MAGNITUDE.value: self.tr("Magnitude, Normal to Boundary"),
        }
        self._profileTypes = {
            VelocityProfile.CONSTANT.value: self.tr("Constant"),
            VelocityProfile.SPATIAL_DISTRIBUTION.value: self.tr("Spatial Distribution"),
            VelocityProfile.TEMPORAL_DISTRIBUTION.value: self.tr("Temporal Distribution"),
        }
        self._setupCombo(self._ui.velocitySpecificationMethod, self._specifications)
        self._setupCombo(self._ui.profileType, self._profileTypes)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)
        self._turbulenceWidget = TurbulenceModelHelper.createWidget(self._xpath)
        self._temperatureWidget = None

        layout = self._ui.dialogContents.layout()
        if self._turbulenceWidget is not None:
            layout.addWidget(self._turbulenceWidget)
        if ModelsDB.isEnergyModelOn():
            self._temperatureWidget = TemperatureWidget(self._xpath, bcid)
            layout.addWidget(self._temperatureWidget)

        self._componentSpatialDistributionFile = None
        self._componentSpatialDistributionFileName = None
        self._componentTemporalDistribution = None
        self._magnitudeSpatialDistributionFile = None
        self._magnitudeSpatialDistributionFileName = None
        self._magnitudeTemporalDistribution = None
        self._dialog = None

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        xpath = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        specification = self._ui.velocitySpecificationMethod.currentData()
        writer.append(xpath + '/velocity/specification', specification, None)
        profile = self._ui.profileType.currentData()
        if specification == VelocitySpecification.COMPONENT.value:
            writer.append(xpath + '/velocity/component/profile', profile, None)
            if profile == VelocityProfile.CONSTANT.value:
                writer.append(xpath + '/velocity/component/constant/x', self._ui.xVelocity.text(),
                              self.tr("X-Velocity"))
                writer.append(xpath + '/velocity/component/constant/y', self._ui.yVelocity.text(),
                              self.tr("Y-Velocity"))
                writer.append(xpath + '/velocity/component/constant/z', self._ui.zVelocity.text(),
                              self.tr("Z-Velocity"))
            elif profile == VelocityProfile.SPATIAL_DISTRIBUTION.value:
                if self._componentSpatialDistributionFile:
                    try:
                        FileDB.putBcFile(self._bcid, BcFileRole.BC_VELOCITY_COMPONENT,
                                         self._componentSpatialDistributionFile)
                    except FileFormatError:
                        QMessageBox.critical(self, self.tr("Input Error"), self.tr("Velocity CSV File is wrong"))
                        return
                elif not self._componentSpatialDistributionFileName:
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("Select Velocity CSV File."))
                    return
            elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION.value:
                if self._componentTemporalDistribution:
                    writer.append(xpath + '/velocity/component/temporalDistribution/piecewiseLinear/t',
                                  self._componentTemporalDistribution[0],
                                  self.tr("Piecewise Linear Velocity"))
                    writer.append(xpath + '/velocity/component/temporalDistribution/piecewiseLinear/x',
                                  self._componentTemporalDistribution[1],
                                  self.tr("Piecewise Linear Velocity"))
                    writer.append(xpath + '/velocity/component/temporalDistribution/piecewiseLinear/y',
                                  self._componentTemporalDistribution[2],
                                  self.tr("Piecewise Linear Velocity"))
                    writer.append(xpath + '/velocity/component/temporalDistribution/piecewiseLinear/z',
                                  self._componentTemporalDistribution[3],
                                  self.tr("Piecewise Linear Velocity"))
                elif self._db.getValue(xpath + '/velocity/component/temporalDistribution/piecewiseLinear/t') == '':
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("Edit Piecewise Linear Velocity."))
                    return
        elif specification == VelocitySpecification.MAGNITUDE.value:
            writer.append(xpath + '/velocity/magnitudeNormal/profile', profile, None)
            if profile == VelocityProfile.CONSTANT.value:
                writer.append(xpath + '/velocity/magnitudeNormal/constant',
                              self._ui.velocityMagnitude.text(), self.tr("Velocity Magnitude"))
            elif profile == VelocityProfile.SPATIAL_DISTRIBUTION.value:
                if self._magnitudeSpatialDistributionFile:
                    try:
                        FileDB.putBcFile(self._bcid, BcFileRole.BC_VELOCITY_MAGNITUDE,
                                         self._magnitudeSpatialDistributionFile)
                    except FileFormatError:
                        QMessageBox.critical(self, self.tr("Input Error"), self.tr("Velocity CSV File is wrong"))
                        return
                elif not self._magnitudeSpatialDistributionFileName:
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("Select Velocity CSV File."))
                    return
            elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION.value:
                if self._magnitudeTemporalDistribution:
                    writer.append(xpath + '/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear/t',
                                  self._magnitudeTemporalDistribution[0],
                                  self.tr("Piecewise Linear Velocity"))
                    writer.append(xpath + '/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear/v',
                                  self._magnitudeTemporalDistribution[1],
                                  self.tr("Piecewise Linear Velocity"))
                elif self._db.getValue(xpath + '/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear/t') == '':
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("Edit Piecewise Linear Velocity."))
                    return

        if self._turbulenceWidget:
            self._turbulenceWidget.appendToWriter(writer)
        if self._temperatureWidget:
            if not self._temperatureWidget.appendToWriter(writer):
                return

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _connectSignalsSlots(self):
        self._ui.velocitySpecificationMethod.currentIndexChanged.connect(self._comboChanged)
        self._ui.profileType.currentIndexChanged.connect(self._comboChanged)
        self._ui.spatialDistributionFileSelect.clicked.connect(self._selectSpatialDistributionFile)
        self._ui.temporalDistributionEdit.clicked.connect(self._editTemporalDistribution)

    def _load(self):
        xpath = self._xpath + self.RELATIVE_XPATH

        specification = self._db.getValue(xpath + '/velocity/specification')
        self._ui.velocitySpecificationMethod.setCurrentText(self._specifications[specification])
        profile = None
        if specification == VelocitySpecification.COMPONENT.value:
            profile = self._db.getValue(xpath + '/velocity/component/profile')
        elif specification == VelocitySpecification.MAGNITUDE.value:
            profile = self._db.getValue(xpath + '/velocity/magnitudeNormal/profile')
        self._componentSpatialDistributionFileName = FileDB.getBcFileName(self._bcid, BcFileRole.BC_VELOCITY_COMPONENT)
        self._magnitudeSpatialDistributionFileName = FileDB.getBcFileName(self._bcid, BcFileRole.BC_VELOCITY_MAGNITUDE)
        self._ui.profileType.setCurrentText(self._profileTypes[profile])
        self._ui.xVelocity.setText(self._db.getValue(xpath + '/velocity/component/constant/x'))
        self._ui.yVelocity.setText(self._db.getValue(xpath + '/velocity/component/constant/y'))
        self._ui.zVelocity.setText(self._db.getValue(xpath + '/velocity/component/constant/z'))
        self._ui.velocityMagnitude.setText(self._db.getValue(xpath + '/velocity/magnitudeNormal/constant'))
        self._comboChanged()

        if self._turbulenceWidget is not None:
            self._turbulenceWidget.load()
        if self._temperatureWidget is not None:
            self._temperatureWidget.load()

    def _setupCombo(self, combo, items):
        for value, text in items.items():
            combo.addItem(text, value)

    def _comboChanged(self):
        specification = self._ui.velocitySpecificationMethod.currentData()
        profile = self._ui.profileType.currentData()

        self._ui.componentConstant.setVisible(
            specification == VelocitySpecification.COMPONENT.value
            and profile == VelocityProfile.CONSTANT.value
        )
        self._ui.magnitudeConsant.setVisible(
            specification == VelocitySpecification.MAGNITUDE.value
            and profile == VelocityProfile.CONSTANT.value
        )

        if profile == VelocityProfile.SPATIAL_DISTRIBUTION.value:
            if specification == VelocitySpecification.COMPONENT.value:
                self._ui.spatialDistributionFileName.setText(self._componentSpatialDistributionFileName)
            elif specification == VelocitySpecification.MAGNITUDE.value:
                self._ui.spatialDistributionFileName.setText(self._magnitudeSpatialDistributionFileName)
            self._ui.spatialDistribution.show()
        else:
            self._ui.spatialDistribution.hide()

        self._ui.temporalDistribution.setVisible(profile == VelocityProfile.TEMPORAL_DISTRIBUTION.value)

    def _selectSpatialDistributionFile(self):
        file = QFileDialog.getOpenFileName(self, self.tr("Open CSV File"), "", self.tr("CSV (*.csv)"))
        if file[0]:
            fileName = path.basename(file[0])
            self._ui.spatialDistributionFileName.setText(fileName)
            specification = self._ui.velocitySpecificationMethod.currentData()
            if specification == VelocitySpecification.COMPONENT.value:
                self._componentSpatialDistributionFile = file[0]
                self._componentSpatialDistributionFileName = fileName
            elif specification == VelocitySpecification.MAGNITUDE.value:
                self._magnitudeSpatialDistributionFile = file[0]
                self._magnitudeSpatialDistributionFileName = fileName

    def _editTemporalDistribution(self):
        if self._ui.velocitySpecificationMethod.currentData() == VelocitySpecification.COMPONENT.value:
            if self._componentTemporalDistribution is None:
                self._componentTemporalDistribution = [
                    self._db.getValue(
                        self._xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear/t'),
                    self._db.getValue(
                        self._xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear/x'),
                    self._db.getValue(
                        self._xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear/y'),
                    self._db.getValue(
                        self._xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear/z'),
                ]
            self._dialog = PiecewiseLinearDialog(self, self.tr("Temporal Distribution"),
                                                 [self.tr("t"), self.tr("Ux"), self.tr("Uy"), self.tr("Uz")],
                                                 self._componentTemporalDistribution)
            self._dialog.accepted.connect(self._componentTemporalDistributionAccepted)
            self._dialog.open()
        elif self._ui.velocitySpecificationMethod.currentData() == VelocitySpecification.MAGNITUDE.value:
            if self._magnitudeTemporalDistribution is None:
                self._magnitudeTemporalDistribution = [
                    self._db.getValue(
                        self._xpath + '/velocityInlet/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear/t'),
                    self._db.getValue(
                        self._xpath + '/velocityInlet/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear/v'),
                ]
            self._dialog = PiecewiseLinearDialog(self, self.tr("Temporal Distribution"),
                                                 [self.tr("t"), self.tr("Umag")],
                                                 self._magnitudeTemporalDistribution)
            self._dialog.accepted.connect(self._magnitudeTemporalDistributionAccepted)
            self._dialog.open()

    def _componentTemporalDistributionAccepted(self):
        self._componentTemporalDistribution = self._dialog.getValues()

    def _magnitudeTemporalDistributionAccepted(self):
        self._magnitudeTemporalDistribution = self._dialog.getValues()
