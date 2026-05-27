#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

import qasync
from PySide6.QtCore import QObject

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox
from widgets.simple_sheet_dialog import SimpleSheetDialog

from baramFlow.base.base import SpatialVectorList, TemporalVectorList, TemporalScalarList, Vector
from baramFlow.base.boundary.boundary_patch import VelocityInletPatch
from baramFlow.base.boundary.velocity_inlet import VelocitySpecification, VelocityProfile, CoordinateSystem
from baramFlow.base.boundary.velocity_inlet import VelocityInlet
from baramFlow.base.boundary.velocity_inlet import InletVelocity, VelocityMagnitude, VelocityComponentCartesian
from baramFlow.base.boundary.velocity_inlet import LocalCylindricalTemporalDistribution, VelocityLocalCylindrical
from baramFlow.base.boundary.velocity_inlet import LocalCylindricalConstant
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .velocity_inlet_dialog_ui import Ui_VelocityInletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class ProfileTypeComboBox(QObject):
    def __init__(self, combo):
        super().__init__()

        self._combo = combo
        self._indexes = None

        self._combo.addItem(self.tr("Constant"), VelocityProfile.CONSTANT)
        self._combo.addItem(self.tr("Spatial Distribution"), VelocityProfile.SPATIAL_DISTRIBUTION)
        self._combo.addItem(self.tr("Temporal Distribution"), VelocityProfile.TEMPORAL_DISTRIBUTION)

        self._indexes = {p: self._combo.findData(p) for p in VelocityProfile}

    def setSpatialDistributionEnabled(self, enabled):
        if enabled:
            self._combo.model().item(self._indexes[VelocityProfile.SPATIAL_DISTRIBUTION]).setEnabled(True)
        else:
            self._combo.model().item(self._indexes[VelocityProfile.SPATIAL_DISTRIBUTION]).setEnabled(False)
            if self._combo.currentData() == VelocityProfile.SPATIAL_DISTRIBUTION:
                self._combo.setCurrentIndex(self._indexes[VelocityProfile.CONSTANT])

    def setCurrentData(self, data):
        self._combo.setCurrentIndex(self._indexes[data])

    def currentData(self):
        return self._combo.currentData()


class VelocityInletDialog(ResizableDialog):
    RELATIVE_XPATH = '/velocityInlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_VelocityInletDialog()
        self._ui.setupUi(self)

        self._bcid = bcid

        self._xpath = BoundaryDB.getXPath(bcid)

        self._profileTypeCombo = ProfileTypeComboBox(self._ui.profileType)

        self._turbulenceWidget = None
        self._temperatureWidget = None
        self._volumeFractionWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        self._componentSpatialDistribution = None
        self._componentTemporalDistribution = None
        self._magnitudeTemporalDistribution = None
        self._velocityComponents = None
        self._dialog = None

        layout = self._ui.dialogContents.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._temperatureWidget = ConditionalWidgetHelper.temperatureWidget(self._xpath, bcid, layout)
        self._volumeFractionWidget = ConditionalWidgetHelper.volumeFractionWidget(rname, layout)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(RegionDB.getMaterial(rname), layout)

        self._ui.velocitySpecificationMethod.addItem(self.tr("Component"),
                                                     VelocitySpecification.COMPONENT)
        self._ui.velocitySpecificationMethod.addItem(self.tr("Magnitude, Normal to Boundary"),
                                                     VelocitySpecification.MAGNITUDE)

        self._ui.coordinateSystem.addItem(self.tr('Cartesian'), CoordinateSystem.CARTESIAN)
        self._ui.coordinateSystem.addItem(self.tr('Local Cylindrical'), CoordinateSystem.LOCAL_CYLINDRICAL)

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        #
        # Validation check for parameters
        #
        valid, msg = self._volumeFractionWidget.validate()
        if not valid:
            await AsyncMessageBox().warning(self, self.tr('Warning'), msg)
            return
        # ToDo: Add validation for other parameters

        try:
            velocityInlet = VelocityInlet(
                velocity=InletVelocity(specificationMethod=self._ui.velocitySpecificationMethod.currentData(),
                                       coordinateSystem=self._ui.coordinateSystem.currentData()))

            profile = VelocityProfile(self._ui.profileType.currentData())

            if velocityInlet.velocity.specificationMethod == VelocitySpecification.MAGNITUDE:
                velocityInlet.velocity.magnitude = VelocityMagnitude(profile=profile)
                if profile == VelocityProfile.CONSTANT:
                    velocityInlet.velocity.magnitude.constant = str(
                        PFloat(self._ui.velocityMagnitude.text(), self.tr('Velocity Magnitude')))
                elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION:
                    velocityInlet.velocity.magnitude.temporalDistribution.piecewiseLinear = self._magnitudeTemporalDistribution
            elif velocityInlet.velocity.coordinateSystem == CoordinateSystem.CARTESIAN:
                velocityInlet.velocity.component = VelocityComponentCartesian(profile=profile)
                if profile == VelocityProfile.CONSTANT:
                    velocityInlet.velocity.component.constant = Vector(
                        x=PFloat(self._ui.xVelocity.text(), self.tr('X-Velocity')),
                        y=PFloat(self._ui.yVelocity.text(), self.tr('Y-Velocity')),
                        z=PFloat(self._ui.zVelocity.text(), self.tr('Z-Velocity')))
                elif profile == VelocityProfile.SPATIAL_DISTRIBUTION:
                    velocityInlet.velocity.component.spatialDistribution = self._componentSpatialDistribution
                elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION:
                    velocityInlet.velocity.component.temporalDistribution.piecewiseLinear = self._componentTemporalDistribution
            else:
                velocityInlet.velocity.localCylindrical = VelocityLocalCylindrical(
                    profile=profile,
                    axisOrigin=self._ui.axisOrigin.vector(self.tr('Axis Origin')),
                    axisDirection=self._ui.axisDirection.vector(self.tr('Axis Direction')))
                if profile == VelocityProfile.CONSTANT:
                    velocityInlet.velocity.localCylindrical.constant = LocalCylindricalConstant(
                        axialVelocity=str(PFloat(self._ui.axialVelocity.text(), self.tr('Axial Velocity'))),
                        radialVelocity=str(PFloat(self._ui.radialVelocity.text(), self.tr('Radiant Velocity'))),
                        angularSpeed=str(PFloat(self._ui.angularSpeed.text(), self.tr('Angular Speed'))))
                elif profile == VelocityProfile.TEMPORAL_DISTRIBUTION:
                    velocityInlet.velocity.localCylindrical.temporalDistribution = self._velocityComponents

            data = VelocityInletPatch(
                velocityInet=velocityInlet,
                userDefinedScalars=self._scalarsWidget.data(),
                species=self._speciesWidget.data(),
                turbulence=self._turbulenceWidget.data(),
                temperature=self._temperatureWidget.data())

            writer = CoreDBWriter()
            if not self._turbulenceWidget.appendToWriter(writer):
                return

            if not await self._volumeFractionWidget.appendToWriter(writer, self._xpath + '/volumeFractions'):
                return

            BoundaryService.updateBoundaryCondition(self._bcid, data, writer)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _connectSignalsSlots(self):
        self._ui.velocitySpecificationMethod.currentIndexChanged.connect(self._onSpecificationMethodChanged)
        self._ui.coordinateSystem.currentIndexChanged.connect(self._onCoordinateSystemChanged)
        self._ui.profileType.currentIndexChanged.connect(self._updateVelocitySettings)
        self._ui.spatialDistributionEdit.clicked.connect(self._onSpatialDistributionEditClicked)
        self._ui.piecewiseLinearEdit.clicked.connect(self._onPiecewiseLinearEditClicked)
        self._ui.velocityComponentsEdit.clicked.connect(self._onVelocityComponentsEditClicked)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        xpath = self._xpath + self.RELATIVE_XPATH

        db = coredb.CoreDB()

        specification = VelocitySpecification(db.getValue(xpath + '/velocity/specification'))
        self._ui.velocitySpecificationMethod.setCurrentIndex(
            self._ui.velocitySpecificationMethod.findData(specification))
        coordinateSystem = CoordinateSystem(db.getValue(xpath + '/velocity/coordinateSystem'))
        self._ui.coordinateSystem.setCurrentIndex(self._ui.coordinateSystem.findData(coordinateSystem))
        profile = None
        if specification == VelocitySpecification.COMPONENT:
            if coordinateSystem == CoordinateSystem.CARTESIAN:
                profile = VelocityProfile(db.getValue(xpath + '/velocity/component/profile'))
            elif coordinateSystem == CoordinateSystem.LOCAL_CYLINDRICAL:
                profile = VelocityProfile(db.getValue(xpath + '/velocity/localCylindrical/profile'))
        elif specification == VelocitySpecification.MAGNITUDE:
            profile = VelocityProfile(db.getValue(xpath + '/velocity/magnitudeNormal/profile'))
        self._ui.profileType.setCurrentIndex(self._ui.profileType.findData(profile))

        self._ui.xVelocity.setText(db.getValue(xpath + '/velocity/component/constant/x'))
        self._ui.yVelocity.setText(db.getValue(xpath + '/velocity/component/constant/y'))
        self._ui.zVelocity.setText(db.getValue(xpath + '/velocity/component/constant/z'))
        self._ui.velocityMagnitude.setText(db.getValue(xpath + '/velocity/magnitudeNormal/constant'))

        self._ui.axialVelocity.setText(db.getValue(xpath + '/velocity/localCylindrical/constant/axialVelocity'))
        self._ui.radialVelocity.setText(db.getValue(xpath + '/velocity/localCylindrical/constant/radialVelocity'))
        self._ui.angularSpeed.setText(db.getValue(xpath + '/velocity/localCylindrical/constant/angularSpeed'))

        self._ui.axisOrigin.setVector(Vector.fromElement(
            db.getElement(xpath + '/velocity/localCylindrical/axisOrigin')))
        self._ui.axisDirection.setVector(Vector.fromElement(
            db.getElement(xpath + '/velocity/localCylindrical/axisDirection')))

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._volumeFractionWidget.load(self._xpath + '/volumeFractions')
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

        self._updateVelocitySettings()

    def _onSpecificationMethodChanged(self):
        self._ui.velocitySettingsType.layout().setRowVisible(
            self._ui.coordinateSystem,
            self._ui.velocitySpecificationMethod.currentData() == VelocitySpecification.COMPONENT)

        self._updateProfileOptions()

    def _onCoordinateSystemChanged(self):
        self._updateProfileOptions()

    def _updateProfileOptions(self):
        self._profileTypeCombo.setSpatialDistributionEnabled(
            self._ui.velocitySpecificationMethod.currentData() == VelocitySpecification.COMPONENT
            and self._ui.coordinateSystem.currentData() == CoordinateSystem.CARTESIAN)

        self._updateVelocitySettings()

    def _updateVelocitySettings(self):
        specification = self._ui.velocitySpecificationMethod.currentData()
        coordinate = self._ui.coordinateSystem.currentData()
        profile = self._profileTypeCombo.currentData()

        isCartesian = False
        isMagnitude = False
        isCylindrical = False

        if specification == VelocitySpecification.MAGNITUDE:
            isMagnitude = True
        elif coordinate == CoordinateSystem.LOCAL_CYLINDRICAL:
            isCylindrical = True
        else:
            isCartesian = True

        self._ui.componentConstant.setVisible(isCartesian and profile == VelocityProfile.CONSTANT)
        self._ui.magnitudeConsant.setVisible(isMagnitude and profile == VelocityProfile.CONSTANT)
        self._ui.spatialDistribution.setVisible(isCartesian and profile == VelocityProfile.SPATIAL_DISTRIBUTION)
        self._ui.cartesianTemporalDistribution.setVisible(
            not isCylindrical and profile == VelocityProfile.TEMPORAL_DISTRIBUTION)
        self._ui.localCylindricalConstant.setVisible(isCylindrical and profile == VelocityProfile.CONSTANT)
        self._ui.localCylindricalTemporalDistribution.setVisible(
            isCylindrical and profile == VelocityProfile.TEMPORAL_DISTRIBUTION)
        self._ui.localCylindrical.setVisible(isCylindrical)

    @qasync.asyncSlot()
    async def _onSpatialDistributionEditClicked(self):
        if self._componentSpatialDistribution is None:
            self._componentSpatialDistribution = SpatialVectorList.fromElement(
                coredb.CoreDB().getElement(self._xpath + '/velocityInlet/velocity/component/spatialDistribution'))

        dialog = SimpleSheetDialog(self, self.tr('Spatial Distribution'), ['x', 'y', 'z', 'Ux', 'Uy', 'Uz'],
                                   self._componentSpatialDistribution.data())
        try:
            self._componentSpatialDistribution = SpatialVectorList(await dialog.show())
        except asyncio.exceptions.CancelledError:
            return

    @qasync.asyncSlot()
    async def _onPiecewiseLinearEditClicked(self):
        if self._ui.velocitySpecificationMethod.currentData() == VelocitySpecification.COMPONENT:
            if self._componentTemporalDistribution is None:
                self._componentTemporalDistribution = TemporalVectorList.fromElement(
                    coredb.CoreDB().getElement(
                        self._xpath + '/velocityInlet/velocity/component/temporalDistribution/piecewiseLinear'))

            dialog = SimpleSheetDialog(self, self.tr('Temporal Distribution'), ['t', 'Ux', 'Uy', 'Uz'],
                                             self._componentTemporalDistribution.data())
            try:
                self._componentTemporalDistribution = TemporalVectorList(await dialog.show())
            except asyncio.exceptions.CancelledError:
                return
        elif self._ui.velocitySpecificationMethod.currentData() == VelocitySpecification.MAGNITUDE:
            if self._magnitudeTemporalDistribution is None:
                self._magnitudeTemporalDistribution = TemporalScalarList.fromElement(
                    coredb.CoreDB().getElement(
                        self._xpath + '/velocityInlet/velocity/magnitudeNormal/temporalDistribution/piecewiseLinear'))

            dialog = SimpleSheetDialog(self, self.tr('Temporal Distribution'), ['t', 'Umag'],
                                       self._magnitudeTemporalDistribution.data())
            try:
                self._magnitudeTemporalDistribution = TemporalScalarList(await dialog.show())
            except asyncio.exceptions.CancelledError:
                return

    @qasync.asyncSlot()
    async def _onVelocityComponentsEditClicked(self):
        if self._velocityComponents is None:
            self._velocityComponents = LocalCylindricalTemporalDistribution.fromElement(
                coredb.CoreDB().getElement(
                    self._xpath + '/velocityInlet/velocity/localCylindrical/temporalDistribution'))

        dialog = SimpleSheetDialog(self, self.tr('Spatial Distribution'), ['t', 'u', 'v', 'ω'],
                                   self._velocityComponents.data())
        try:
            self._velocityComponents = LocalCylindricalTemporalDistribution(await dialog.show())
        except asyncio.exceptions.CancelledError:
            return
