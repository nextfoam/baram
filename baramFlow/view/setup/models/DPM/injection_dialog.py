#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
from typing import cast

import qasync
from PySide6.QtWidgets import QDialog, QFormLayout

from baramFlow.base.base import Vector
from baramFlow.coredb.general_db import GeneralDB
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.base.constants import Function1Type
from baramFlow.base.model.model import DPMFlowRateSpec, DPMInjectionType, DPMConeInjectorType, DPMParticleSpeed
from baramFlow.base.model.model import DPMParticleVelocityType, DPMDiameterDistribution, DPM_INJECTION_TYPE_TEXTS
from baramFlow.coredb.boundary_db import BoundaryDB
from widgets.simple_sheet_dialog import SimpleSheetDialog
from .injection_dialog_ui import Ui_InjectionDialog


class InjectionDialog(QDialog):
    def __init__(self, parent, injection, usedNames):
        super().__init__(parent)
        self._ui = Ui_InjectionDialog()
        self._ui.setupUi(self)

        self._injection = injection
        self._usedNames = usedNames

        self._positions = None
        self._surface = None

        transient = GeneralDB.isTimeTransient()
        if transient:
            availableFunction1Types = [Function1Type.CONSTANT, Function1Type.TABLE]
        else:
            availableFunction1Types = [Function1Type.CONSTANT]

        self._ui.injectionType.addItem(DPM_INJECTION_TYPE_TEXTS[DPMInjectionType.POINT],    DPMInjectionType.POINT)
        self._ui.injectionType.addItem(DPM_INJECTION_TYPE_TEXTS[DPMInjectionType.SURFACE],  DPMInjectionType.SURFACE)
        self._ui.injectionType.addItem(DPM_INJECTION_TYPE_TEXTS[DPMInjectionType.CONE],     DPMInjectionType.CONE)

        self._ui.flowRateSpec.addItem(self.tr('Particle Count'),    DPMFlowRateSpec.PARTICLE_COUNT)
        self._ui.flowRateSpec.addItem(self.tr('Particle Volume'),   DPMFlowRateSpec.PARTICLE_VOLUME)

        layout = cast(QFormLayout, self._ui.particleVolumeParameters.layout())
        layout.setRowVisible(self._ui.totalMass,      transient)
        layout.setRowVisible(self._ui.volumeFlowRate, transient)
        layout.setRowVisible(self._ui.massFlowRate,   not transient)

        if not transient:
            self._ui.startStopTime.hide()

        self._ui.volumeFlowRate.setup(availableFunction1Types)

        self._ui.coneInjectorType.addItem(self.tr('Point'), DPMConeInjectorType.POINT)
        self._ui.coneInjectorType.addItem(self.tr('Disc'),  DPMConeInjectorType.DISC)

        self._ui.conePosition.setup(availableFunction1Types)
        self._ui.coneAxis.setup(availableFunction1Types)
        self._ui.outerConeAngle.setup(availableFunction1Types)
        self._ui.innerConeAngle.setup(availableFunction1Types)
        self._ui.swirlVelocity.setup(availableFunction1Types)

        self._ui.coneParticleSpeed.addItem(self.tr('from Injection Speed'), DPMParticleSpeed.FROM_INJECTION_SPEED)
        self._ui.coneParticleSpeed.addItem(self.tr('from Pressure'),        DPMParticleSpeed.FROM_PRESSURE)
        self._ui.coneParticleSpeed.addItem(self.tr('from Discharge Coeff'), DPMParticleSpeed.FROM_DISCHARGE_COEFF)

        self._ui.injectorPressure.setup(availableFunction1Types)
        self._ui.dischargeCoeff.setup(availableFunction1Types)

        self._ui.surfaceParticleVelocityType.addItem(self.tr('Constant'),      DPMParticleVelocityType.CONSTANT)
        self._ui.surfaceParticleVelocityType.addItem(self.tr('Face-Value'),    DPMParticleVelocityType.FACE_VALUE)
        self._ui.surfaceParticleVelocityType.addItem(self.tr('Cell-Value'),    DPMParticleVelocityType.CELL_VALUE)

        self._ui.diameterDistribution.addItem(self.tr('Uniform'),
                                              DPMDiameterDistribution.UNIFORM)
        self._ui.diameterDistribution.addItem(self.tr('Linear'),
                                              DPMDiameterDistribution.LINEAR)
        self._ui.diameterDistribution.addItem(self.tr('Rosin-Rammler'),
                                              DPMDiameterDistribution.ROSIN_RAMMLER)
        self._ui.diameterDistribution.addItem(self.tr('Mass-Rosin-Rammler'),
                                              DPMDiameterDistribution.MASS_ROSIN_RAMMLER)
        self._ui.diameterDistribution.addItem(self.tr('Normal'),
                                              DPMDiameterDistribution.NORMAL)

        self._injectionTypeChanged()
        self._flowRateSpecChanged()
        self._coneInjectorTypeChanged()
        self._coneParticleSpeedChanged()
        self._diameterDistributionChanged()

        self._connectSignalsSlots()

        self._ui.injectionType.setCurrentIndex(self._ui.injectionType.findData(DPMInjectionType.CONE))
        self.adjustSize()

        self._load()

    def injection(self):
        return self._injection

    def _connectSignalsSlots(self):
        self._ui.injectionType.currentIndexChanged.connect(self._injectionTypeChanged)
        self._ui.editPosition.clicked.connect(self._opePositionEditor)
        self._ui.flowRateSpec.currentIndexChanged.connect(self._flowRateSpecChanged)
        self._ui.surfaceParticleVelocityType.currentIndexChanged.connect(self._surfaceParticleVelocityTypeChanged)
        self._ui.surfaceSelect.clicked.connect(self._openSurfaceSelector)
        self._ui.coneInjectorType.currentIndexChanged.connect(self._coneInjectorTypeChanged)
        self._ui.coneParticleSpeed.currentIndexChanged.connect(self._coneParticleSpeedChanged)
        self._ui.diameterDistribution.currentIndexChanged.connect(self._diameterDistributionChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        self._ui.name.setText(self._injection.name)
        self._ui.injectionType.setCurrentIndex(self._ui.injectionType.findData(self._injection.injector.type))

        self._ui.numberOfParticlesPerPoint.setBatchableNumber(
            self._injection.injector.pointInjection.numberOfParticlesPerPoint)
        self._ui.injectionTime.setBatchableNumber(self._injection.injector.pointInjection.injectionTime)
        self._ui.pointParticleVelocity.setVector(self._injection.injector.pointInjection.particleVelocity)

        self._ui.flowRateSpec.setCurrentIndex(
            self._ui.flowRateSpec.findData(self._injection.injector.flowRate.specification))
        self._ui.countParcelPerSecond.setBatchableNumber(
            self._injection.injector.flowRate.particleCount.parcelPerSecond)
        self._ui.numberOfParticlesPerParcel.setBatchableNumber(
            self._injection.injector.flowRate.particleCount.numberOfParticlesPerParcel)
        self._ui.volumeParcelPerSecond.setBatchableNumber(
            self._injection.injector.flowRate.particleVolume.parcelPerSecond)
        self._ui.totalMass.setBatchableNumber(self._injection.injector.flowRate.particleVolume.totalMass)
        self._ui.volumeFlowRate.setData(self._injection.injector.flowRate.particleVolume.volumeFlowRate)
        self._ui.massFlowRate.setBatchableNumber(self._injection.injector.flowRate.particleVolume.massFlowRate)
        self._ui.startTime.setBatchableNumber(self._injection.injector.flowRate.startTime)
        self._ui.stopTime.setBatchableNumber(self._injection.injector.flowRate.stopTime)

        self._ui.surfaceParticleVelocityType.setCurrentIndex(
            self._ui.surfaceParticleVelocityType.findData(
                self._injection.injector.surfaceInjection.particleVelocity.type))
        self._ui.surfaceParticleVelocity.setVector(self._injection.injector.surfaceInjection.particleVelocity.value)
        self._setSurface(self._injection.injector.surfaceInjection.bcid)

        self._ui.coneInjectorType.setCurrentIndex(
            self._ui.coneInjectorType.findData(self._injection.injector.coneInjection.injectorType))
        self._ui.conePosition.setData(self._injection.injector.coneInjection.position)
        self._ui.coneAxis.setData(self._injection.injector.coneInjection.axis)
        self._ui.outerConeAngle.setData(self._injection.injector.coneInjection.outerConeAngle)
        self._ui.innerConeAngle.setData(self._injection.injector.coneInjection.innerConeAngle)
        self._ui.outerRadius.setBatchableNumber(self._injection.injector.coneInjection.outerRadius)
        self._ui.innerRadius.setBatchableNumber(self._injection.injector.coneInjection.innerRadius)
        self._ui.swirlVelocity.setData(self._injection.injector.coneInjection.swirlVelocity)
        self._ui.coneParticleSpeed.setCurrentIndex(
            self._ui.coneParticleSpeed.findData(self._injection.injector.coneInjection.particleSpeed))
        self._ui.injectionSpeed.setBatchableNumber(self._injection.injector.coneInjection.injectionSpeed)
        self._ui.injectorPressure.setData(self._injection.injector.coneInjection.injectorPressure)
        self._ui.dischargeCoeff.setData(self._injection.injector.coneInjection.dischargeCoeff)

        self._ui.diameterDistribution.setCurrentIndex(
            self._ui.diameterDistribution.findData(self._injection.diameterDistribution.type))
        self._ui.diameter.setBatchableNumber(self._injection.diameterDistribution.diameter)
        self._ui.minDiameter.setBatchableNumber(self._injection.diameterDistribution.minDiameter)
        self._ui.maxDiameter.setBatchableNumber(self._injection.diameterDistribution.maxDiameter)
        self._ui.meanDiameter.setBatchableNumber(self._injection.diameterDistribution.meanDiameter)
        self._ui.spreadParameter.setBatchableNumber(self._injection.diameterDistribution.spreadParameter)
        self._ui.stdDeviation.setBatchableNumber(self._injection.diameterDistribution.stdDeviation)

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name == '':
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Injection Name is required.'))
            return

        if name != self._injection.name and name in self._usedNames:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Injection Name "{}" is already used.').format(name))
            return

        injectionType = self._ui.injectionType.currentData()
        flowRateSpec = self._ui.flowRateSpec.currentData()
        coneInjectorType = self._ui.coneInjectorType.currentData()
        coneParticleSpeed = self._ui.coneParticleSpeed.currentData()
        diameterDistribution = self._ui.diameterDistribution.currentData()

        try:
            if injectionType == DPMInjectionType.POINT:
                self._ui.numberOfParticlesPerPoint.validate(self.tr('Number of Particles per Point'))
                self._ui.injectionTime.validate(self.tr('Injection Time'), low=0, lowInclusive=True)
                self._ui.pointParticleVelocity.validate(self.tr('Particle Velocity'))
            else:
                if flowRateSpec == DPMFlowRateSpec.PARTICLE_COUNT:
                    self._ui.countParcelPerSecond.validate(self.tr('Parcels per Second'), low=0, lowInclusive=False)
                    self._ui.numberOfParticlesPerParcel.validate(self.tr('Number of Particles per Pacel'),
                                                                 low=0, lowInclusive=False)
                elif flowRateSpec == DPMFlowRateSpec.PARTICLE_VOLUME:
                    self._ui.volumeParcelPerSecond.validate(self.tr('Parcels per Second'), low=0, lowInclusive=False)
                    self._ui.totalMass.validate(self.tr('Total Mass'), low=0, lowInclusive=False)
                    self._ui.volumeFlowRate.validate(self.tr('Volume FlowRate'), low=0)
                    self._ui.massFlowRate.validate(self.tr('Mass Flow Rate'), low=0, lowInclusive=False)

                self._ui.startTime.validate(self.tr('Start Time'), low=0, lowInclusive=True)
                self._ui.stopTime.validate(self.tr('Stop Time'))
                if self._ui.startTime.validatedFloat() >= self._ui.stopTime.validatedFloat():
                    await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                        self.tr('Stop Time must be greater than Start Time.'))
                    return

                if injectionType == DPMInjectionType.SURFACE:
                    self._ui.surfaceParticleVelocity.validate(self.tr('Particle Velocity'))
                    if self._surface == '0':
                        await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Surface.'))
                        return
                elif injectionType == DPMInjectionType.CONE:
                    self._ui.conePosition.validate(self.tr('Position'))
                    self._ui.coneAxis.validate(self.tr('Axis'))
                    self._ui.outerConeAngle.validate(self.tr('Outer Cone Angle'), low=0)
                    self._ui.innerConeAngle.validate(self.tr('Inner Cone Angle'), low=0)

                    if coneInjectorType == DPMConeInjectorType.DISC:
                        self._ui.outerRadius.validate(self.tr('Outer Radius'))
                        self._ui.innerRadius.validate(self.tr('Inner Radius'), low=0)
                        if self._ui.outerRadius.validatedFloat() < self._ui.innerRadius.validatedFloat():
                            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                                self.tr('Inner Radius must be less than Outer Radius.'))
                            return

                    self._ui.swirlVelocity.validate(self.tr('Swirl Velocity'), low=0)

                    if coneParticleSpeed == DPMParticleSpeed.FROM_INJECTION_SPEED:
                        self._ui.injectionSpeed.validate(self.tr('Injection Speed'), low=0)
                    elif coneParticleSpeed == DPMParticleSpeed.FROM_PRESSURE:
                        self._ui.injectorPressure.validate(self.tr('Injection Pressure'), low=0)
                    elif coneParticleSpeed == DPMParticleSpeed.FROM_DISCHARGE_COEFF:
                        self._ui.dischargeCoeff.validate(self.tr('Discharge Coeff'), low=0)

            if diameterDistribution == DPMDiameterDistribution.UNIFORM:
                self._ui.diameter.validate(self.tr('Diameter'), low=0, lowInclusive=False)
            else:
                self._ui.minDiameter.validate(self.tr('Min. Diameter'), low=0, lowInclusive=False)
                self._ui.maxDiameter.validate(self.tr('Max. Diameter'))
                if self._ui.minDiameter.validatedFloat() > self._ui.maxDiameter.validatedFloat():
                    await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                        self.tr('Max. Diameter must be greater than Min. Diameter.'))
                    return
                if diameterDistribution != DPMDiameterDistribution.LINEAR:
                    self._ui.meanDiameter.validate(self.tr('Mean Diameter'))
                    if diameterDistribution in (
                            DPMDiameterDistribution.ROSIN_RAMMLER, DPMDiameterDistribution.MASS_ROSIN_RAMMLER):
                        self._ui.spreadParameter.validate(self.tr('Spread Parameter'), low=0, lowInclusive=False)
                    elif diameterDistribution == DPMDiameterDistribution.NORMAL:
                        self._ui.stdDeviation.validate(self.tr('Std. Deviation'), low=0, lowInclusive=False)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self._injection.name = self._ui.name.text()
        self._injection.injector.type = injectionType
        if injectionType == DPMInjectionType.POINT:
            self._injection.injector.pointInjection.numberOfParticlesPerPoint = self._ui.numberOfParticlesPerPoint.batchableNumber()
            self._injection.injector.pointInjection.injectionTime = self._ui.injectionTime.batchableNumber()
            self._injection.injector.pointInjection.particleVelocity = self._ui.pointParticleVelocity.vector()
            if self._positions is not None:  # is edited
                self._injection.injector.pointInjection.positions = self._positions
        else:
            self._injection.injector.flowRate.specification = flowRateSpec
            if flowRateSpec == DPMFlowRateSpec.PARTICLE_COUNT:
                self._injection.injector.flowRate.particleCount.parcelPerSecond = self._ui.countParcelPerSecond.batchableNumber()
                self._injection.injector.flowRate.particleCount.numberOfParticlesPerParcel = self._ui.numberOfParticlesPerParcel.batchableNumber()
            elif flowRateSpec == DPMFlowRateSpec.PARTICLE_VOLUME:
                self._injection.injector.flowRate.particleVolume.parcelPerSecond = self._ui.volumeParcelPerSecond.batchableNumber()
                self._injection.injector.flowRate.particleVolume.totalMass = self._ui.totalMass.batchableNumber()
                self._ui.volumeFlowRate.updateData(self._injection.injector.flowRate.particleVolume.volumeFlowRate)
                self._injection.injector.flowRate.particleVolume.massFlowRate = self._ui.massFlowRate.batchableNumber()

            self._injection.injector.flowRate.startTime = self._ui.startTime.batchableNumber()
            self._injection.injector.flowRate.stopTime = self._ui.stopTime.batchableNumber()

            self._injection.injector.coneInjection.injectorType = coneInjectorType
            if injectionType == DPMInjectionType.SURFACE:
                self._injection.injector.surfaceInjection.particleVelocity.type = self._ui.surfaceParticleVelocityType.currentData()
                self._injection.injector.surfaceInjection.particleVelocity.value = self._ui.surfaceParticleVelocity.vector()
                self._injection.injector.surfaceInjection.bcid = self._surface
            elif injectionType == DPMInjectionType.CONE:
                self._ui.conePosition.updateData(self._injection.injector.coneInjection.position)
                self._ui.coneAxis.updateData(self._injection.injector.coneInjection.axis)
                self._ui.outerConeAngle.updateData(self._injection.injector.coneInjection.outerConeAngle)
                self._ui.innerConeAngle.updateData(self._injection.injector.coneInjection.innerConeAngle)

                if coneInjectorType == DPMConeInjectorType.DISC:
                    self._injection.injector.coneInjection.outerRadius = self._ui.outerRadius.batchableNumber()
                    self._injection.injector.coneInjection.innerRadius = self._ui.innerRadius.batchableNumber()

                self._ui.swirlVelocity.updateData(self._injection.injector.coneInjection.swirlVelocity)

                self._injection.injector.coneInjection.particleSpeed = coneParticleSpeed
                if coneParticleSpeed == DPMParticleSpeed.FROM_INJECTION_SPEED:
                    self._injection.injector.coneInjection.injectionSpeed= self._ui.injectionSpeed.batchableNumber()
                elif coneParticleSpeed == DPMParticleSpeed.FROM_PRESSURE:
                    self._ui.injectorPressure.updateData(self._injection.injector.coneInjection.injectorPressure)
                elif coneParticleSpeed == DPMParticleSpeed.FROM_DISCHARGE_COEFF:
                    self._ui.dischargeCoeff.updateData(self._injection.injector.coneInjection.dischargeCoeff)

        self._injection.diameterDistribution.type = diameterDistribution
        if diameterDistribution == DPMDiameterDistribution.UNIFORM:
            self._injection.diameterDistribution.diameter = self._ui.diameter.batchableNumber()
        else:
            self._injection.diameterDistribution.minDiameter = self._ui.minDiameter.batchableNumber()
            self._injection.diameterDistribution.maxDiameter = self._ui.maxDiameter.batchableNumber()
            if diameterDistribution != DPMDiameterDistribution.LINEAR:
                self._injection.diameterDistribution.meanDiameter = self._ui.meanDiameter.batchableNumber()
                if diameterDistribution in (
                        DPMDiameterDistribution.ROSIN_RAMMLER, DPMDiameterDistribution.MASS_ROSIN_RAMMLER):
                    self._injection.diameterDistribution.spreadParameter = self._ui.spreadParameter.batchableNumber()
                elif diameterDistribution == DPMDiameterDistribution.NORMAL:
                    self._injection.diameterDistribution.stdDeviation = self._ui.stdDeviation.batchableNumber()

        self.accept()

    def _setSurface(self, bcid):
        self._surface = bcid
        if self._surface != '0':
            self._ui.surface.setText(BoundaryDB.getBoundaryName(self._surface))

    def _injectionTypeChanged(self):
        type_ = self._ui.injectionType.currentData()
        self._ui.pointInjection.setVisible(type_ == DPMInjectionType.POINT)
        self._ui.flowRate.setVisible(type_ != DPMInjectionType.POINT)
        self._ui.surfaceInjection.setVisible(type_ == DPMInjectionType.SURFACE)
        self._ui.coneInjection.setVisible(type_ == DPMInjectionType.CONE)

    @qasync.asyncSlot()
    async def _opePositionEditor(self):
        if self._positions is None:
            self._positions = self._injection.injector.pointInjection.positions

        dialog = SimpleSheetDialog(
            self, ['x', 'y', 'z'],
            [[float(row.x.text), float(row.y.text), float(row.z.text)] for row in self._positions])
        try:
            self._positions = [Vector.new(str(x), str(y), str(z)) for x, y, z in await dialog.show()]
        except asyncio.exceptions.CancelledError:
            return

    def _flowRateSpecChanged(self):
        spec = self._ui.flowRateSpec.currentData()
        if spec == DPMFlowRateSpec.PARTICLE_COUNT:
            self._ui.particleCountParameters.show()
            self._ui.particleVolumeParameters.hide()
        else:
            self._ui.particleCountParameters.hide()
            self._ui.particleVolumeParameters.show()

    def _surfaceParticleVelocityTypeChanged(self):
        velocityType: DPMParticleVelocityType = self._ui.surfaceParticleVelocityType.currentData()
        self._ui.surfaceParticleVelocity.setEnabled(velocityType == DPMParticleVelocityType.CONSTANT)

    def _openSurfaceSelector(self):
        def surfaceSelected():
            self._setSurface(self._dialog.selectedItem())

        self._dialog = SelectorDialog(self, self.tr("Select Surface"), self.tr("Select Surface"),
                                      BoundaryDB.getBoundarySelectorItems())
        self._dialog.accepted.connect(surfaceSelected)
        self._dialog.open()

    def _coneInjectorTypeChanged(self):
        type_ = self._ui.coneInjectorType.currentData()
        layout = cast(QFormLayout, self._ui.coneInjection.layout())
        if type_ == DPMConeInjectorType.POINT:
            layout.setRowVisible(self._ui.outerRadius, False)
            layout.setRowVisible(self._ui.innerRadius, False)
        else:
            layout.setRowVisible(self._ui.outerRadius, True)
            layout.setRowVisible(self._ui.innerRadius, True)

    def _coneParticleSpeedChanged(self):
        particleSpeed = self._ui.coneParticleSpeed.currentData()
        layout = cast(QFormLayout, self._ui.coneInjection.layout())
        layout.setRowVisible(self._ui.injectionSpeed, particleSpeed == DPMParticleSpeed.FROM_INJECTION_SPEED)
        layout.setRowVisible(self._ui.injectorPressure, particleSpeed == DPMParticleSpeed.FROM_PRESSURE)
        layout.setRowVisible(self._ui.dischargeCoeff, particleSpeed == DPMParticleSpeed.FROM_DISCHARGE_COEFF)

    def _diameterDistributionChanged(self):
        distribution = self._ui.diameterDistribution.currentData()
        layout = cast(QFormLayout, self._ui.diameterParameters.layout())
        if distribution == DPMDiameterDistribution.UNIFORM:
            layout.setRowVisible(self._ui.diameter, True)
            layout.setRowVisible(self._ui.minDiameter, False)
            layout.setRowVisible(self._ui.maxDiameter, False)
            layout.setRowVisible(self._ui.meanDiameter, False)
            layout.setRowVisible(self._ui.spreadParameter, False)
            layout.setRowVisible(self._ui.stdDeviation, False)
        elif distribution == DPMDiameterDistribution.LINEAR:
            layout.setRowVisible(self._ui.diameter, False)
            layout.setRowVisible(self._ui.minDiameter, True)
            layout.setRowVisible(self._ui.maxDiameter, True)
            layout.setRowVisible(self._ui.meanDiameter, False)
            layout.setRowVisible(self._ui.spreadParameter, False)
            layout.setRowVisible(self._ui.stdDeviation, False)
        elif distribution in (DPMDiameterDistribution.ROSIN_RAMMLER, DPMDiameterDistribution.MASS_ROSIN_RAMMLER):
            layout.setRowVisible(self._ui.diameter, False)
            layout.setRowVisible(self._ui.minDiameter, True)
            layout.setRowVisible(self._ui.maxDiameter, True)
            layout.setRowVisible(self._ui.meanDiameter, True)
            layout.setRowVisible(self._ui.spreadParameter, True)
            layout.setRowVisible(self._ui.stdDeviation, False)
        elif distribution == DPMDiameterDistribution.NORMAL:
            layout.setRowVisible(self._ui.diameter, False)
            layout.setRowVisible(self._ui.minDiameter, True)
            layout.setRowVisible(self._ui.maxDiameter, True)
            layout.setRowVisible(self._ui.meanDiameter, True)
            layout.setRowVisible(self._ui.spreadParameter, False)
            layout.setRowVisible(self._ui.stdDeviation, True)
