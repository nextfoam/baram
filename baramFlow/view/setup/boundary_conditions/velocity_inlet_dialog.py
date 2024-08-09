#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import qasync
from PySide6.QtWidgets import QFileDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.filedb import BcFileRole, FileFormatError
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB, VelocitySpecification, VelocityProfile
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.project import Project
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from baramFlow.view.widgets.number_input_dialog import PiecewiseLinearDialog
from .velocity_inlet_dialog_ui import Ui_VelocityInletDialog
from .conditional_widget_helper import ConditionalWidgetHelper

PROFILE_TYPE_SPATIAL_DISTRIBUTION_INDEX = 1


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

        self._xpath = BoundaryDB.getXPath(bcid)

        self._turbulenceWidget = None
        self._temperatureWidget = None
        self._volumeFractionWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        self._componentSpatialDistributionFile = None
        self._componentSpatialDistributionFileName = None
        self._componentTemporalDistribution = None
        self._magnitudeSpatialDistributionFile = None
        self._magnitudeSpatialDistributionFileName = None
        self._magnitudeTemporalDistribution = None
        self._dialog = None

        layout = self._ui.dialogContents.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._temperatureWidget = ConditionalWidgetHelper.temperatureWidget(self._xpath, bcid, layout)
        self._volumeFractionWidget = ConditionalWidgetHelper.volumeFractionWidget(rname, layout)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(RegionDB.getMaterial(rname), layout)

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        xpath = self._xpath + self.RELATIVE_XPATH
        fileDB = Project.instance().fileDB()
        db = coredb.CoreDB()

        oldDistributionFileKey = None
        distributionFileKey = None

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
                        oldDistributionFileKey = db.getValue(xpath + '/velocity/component/spatialDistribution')
                        distributionFileKey = fileDB.putBcFile(self._bcid, BcFileRole.BC_VELOCITY_COMPONENT,
                                                               self._componentSpatialDistributionFile)
                        writer.append(xpath + '/velocity/component/spatialDistribution', distributionFileKey, None)
                    except FileFormatError:
                        await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                            self.tr("Velocity CSV File is wrong"))
                        return
                elif not self._componentSpatialDistributionFileName:
                    await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                        self.tr("Select Velocity CSV File."))
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
                elif db.getValue(xpath + '/velocity/component/temporalDistribution/piecewiseLinear/t') == '':
                    await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                        self.tr("Edit Piecewise Linear Velocity."))
                    return
        elif specification == VelocitySpecification.MAGNITUDE.value:
            writer.append(xpath + '/velocity/magnitudeNormal/profile', profile, None)
            if profile == VelocityProfile.CONSTANT.value:
                writer.append(xpath + '/velocity/magnitudeNormal/constant',
                              self._ui.velocityMagnitude.text(), self.tr("Velocity Magnitude"))
            elif profile == VelocityProfile.SPATIAL_DISTRIBUTION.value:
                if self._magnitudeSpatialDistributionFile:
                    try:
                        oldDistributionFileKey = db.getVale(
                            xpath + '/velocity/magnitudeNormal/spatialDistribution')
                        distributionFileKey = fileDB.putBcFile(self._bcid, BcFileRole.BC_VELOCITY_MAGNITUDE,
                                                               self._magnitudeSpatialDistributionFile)
                        writer.append(xpath + '/velocity/magnitudeNormal/spatialDistribution',
                                      distributionFileKey, None)
                    except FileFormatError:
                        await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                            self.tr("Velocity CSV File is wrong"))
                        return
                elif not self._magnitudeSpatialDistributionFileName:
                    await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                        self.tr("Select Velocity CSV File."))
                    return
            elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION.value:
                if self._magnitudeTemporalDistribution:
                    writer.append(xpath + '/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear/t',
                                  self._magnitudeTemporalDistribution[0],
                                  self.tr("Piecewise Linear Velocity"))
                    writer.append(xpath + '/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear/v',
                                  self._magnitudeTemporalDistribution[1],
                                  self.tr("Piecewise Linear Velocity"))
                elif db.getValue(xpath + '/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear/t') == '':
                    await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                        self.tr("Edit Piecewise Linear Velocity."))
                    return

        if not self._turbulenceWidget.appendToWriter(writer):
            return

        if not self._temperatureWidget.appendToWriter(writer):
            return

        if not await self._volumeFractionWidget.appendToWriter(writer, self._xpath + '/volumeFractions'):
            return

        if not self._scalarsWidget.appendToWriter(writer, self._xpath + '/userDefinedScalars'):
            return

        if not await self._speciesWidget.appendToWriter(writer, self._xpath + '/species'):
            return

        errorCount = writer.write()
        if errorCount > 0:
            if distributionFileKey:
                fileDB.delete(distributionFileKey)

            self._temperatureWidget.rollbackWriting()
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            ## For the copy boundary conditions feature, old key should not be deleted.
            # if distributionFileKey and oldDistributionFileKey:
            #     fileDB.delete(oldDistributionFileKey)
            #
            self._temperatureWidget.completeWriting()
            self.accept()

    def _connectSignalsSlots(self):
        self._ui.velocitySpecificationMethod.currentIndexChanged.connect(self._comboChanged)
        self._ui.profileType.currentIndexChanged.connect(self._comboChanged)
        self._ui.spatialDistributionFileSelect.clicked.connect(self._selectSpatialDistributionFile)
        self._ui.temporalDistributionEdit.clicked.connect(self._editTemporalDistribution)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        xpath = self._xpath + self.RELATIVE_XPATH

        filedb = Project.instance().fileDB()
        db = coredb.CoreDB()

        specification = db.getValue(xpath + '/velocity/specification')
        self._ui.velocitySpecificationMethod.setCurrentText(self._specifications[specification])
        profile = None
        if specification == VelocitySpecification.COMPONENT.value:
            profile = db.getValue(xpath + '/velocity/component/profile')
        elif specification == VelocitySpecification.MAGNITUDE.value:
            profile = db.getValue(xpath + '/velocity/magnitudeNormal/profile')
        self._componentSpatialDistributionFileName = filedb.getUserFileName(
            db.getValue(xpath + '/velocity/component/spatialDistribution'))
        self._magnitudeSpatialDistributionFileName = filedb.getUserFileName(
            db.getValue(xpath + '/velocity/magnitudeNormal/spatialDistribution'))
        self._ui.profileType.setCurrentText(self._profileTypes[profile])
        self._ui.xVelocity.setText(db.getValue(xpath + '/velocity/component/constant/x'))
        self._ui.yVelocity.setText(db.getValue(xpath + '/velocity/component/constant/y'))
        self._ui.zVelocity.setText(db.getValue(xpath + '/velocity/component/constant/z'))
        self._ui.velocityMagnitude.setText(db.getValue(xpath + '/velocity/magnitudeNormal/constant'))
        self._comboChanged()

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._volumeFractionWidget.load(self._xpath + '/volumeFractions')
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

    def _setupCombo(self, combo, items):
        for value, text in items.items():
            combo.addItem(text, value)

    def _comboChanged(self):
        specification = self._ui.velocitySpecificationMethod.currentData()
        profile = self._ui.profileType.currentData()

        if specification == VelocitySpecification.MAGNITUDE.value:
            self._ui.profileType.model().item(PROFILE_TYPE_SPATIAL_DISTRIBUTION_INDEX).setEnabled(False)
            if self._ui.profileType.currentData() == VelocityProfile.SPATIAL_DISTRIBUTION.value:
                profile = VelocityProfile.CONSTANT.value
                self._ui.profileType.setCurrentText(self._profileTypes[profile])
        else:
            self._ui.profileType.model().item(PROFILE_TYPE_SPATIAL_DISTRIBUTION_INDEX).setEnabled(True)

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
        self._dialog = QFileDialog(self, self.tr('Select CSV File'), '', 'CSV (*.csv)')
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._dialog.accepted.connect(self._spatialDistributionFileSelected)
        self._dialog.open()

    def _editTemporalDistribution(self):
        db = coredb.CoreDB()
        if self._ui.velocitySpecificationMethod.currentData() == VelocitySpecification.COMPONENT.value:
            if self._componentTemporalDistribution is None:
                self._componentTemporalDistribution = [
                    db.getValue(
                        self._xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear/t'),
                    db.getValue(
                        self._xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear/x'),
                    db.getValue(
                        self._xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear/y'),
                    db.getValue(
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
                    db.getValue(
                        self._xpath + '/velocityInlet/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear/t'),
                    db.getValue(
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

    def _spatialDistributionFileSelected(self):
        if files := self._dialog.selectedFiles():
            file = Path(files[0])
            self._ui.spatialDistributionFileName.setText(file.name)
            specification = self._ui.velocitySpecificationMethod.currentData()
            if specification == VelocitySpecification.COMPONENT.value:
                self._componentSpatialDistributionFile = file
                self._componentSpatialDistributionFileName = file.name
            elif specification == VelocitySpecification.MAGNITUDE.value:
                self._magnitudeSpatialDistributionFile = file
                self._magnitudeSpatialDistributionFileName = file.name
