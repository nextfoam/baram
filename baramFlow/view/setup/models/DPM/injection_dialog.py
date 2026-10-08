#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import copy
from typing import cast

import qasync
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QWidget

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog
from widgets.simple_sheet_dialog import SimpleSheetDialog

from baramFlow.base.base import Vector
from baramFlow.base.constants import Function1Type
from baramFlow.base.model.DPM_model import Injection
from baramFlow.base.model.model import DPMFlowRateSpec, DPMInjectionType, DPMConeInjectorType, DPMParticleSpeed
from baramFlow.base.model.model import DPMParticleVelocityType, DPMDiameterDistribution, DPM_INJECTION_TYPE_TEXTS
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.general_db import GeneralDB
from .injection_dialog_ui import Ui_InjectionDialog


class InjectionDialog(QDialog):
    dataAccepted = Signal(Injection)

    def __init__(self, parent: QWidget, injection: Injection, usedNames: list[str]):
        super().__init__(parent)
        self._ui = Ui_InjectionDialog()
        self._ui.setupUi(self)

        self._data: Injection = injection
        self._usedNames: list[str] = usedNames

        self._positions: list[Vector] | None = None
        self._surface: str = '0'

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

    def _connectSignalsSlots(self):
        self._ui.injectionType.currentIndexChanged.connect(self._injectionTypeChanged)
        self._ui.editPosition.clicked.connect(self._openPositionEditor)
        self._ui.flowRateSpec.currentIndexChanged.connect(self._flowRateSpecChanged)
        self._ui.surfaceParticleVelocityType.currentIndexChanged.connect(self._surfaceParticleVelocityTypeChanged)
        self._ui.surfaceSelect.clicked.connect(self._openSurfaceSelector)
        self._ui.coneInjectorType.currentIndexChanged.connect(self._coneInjectorTypeChanged)
        self._ui.coneParticleSpeed.currentIndexChanged.connect(self._coneParticleSpeedChanged)
        self._ui.diameterDistribution.currentIndexChanged.connect(self._diameterDistributionChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        self._ui.name.setText(self._data.name)
        self._ui.injectionType.setCurrentIndex(self._ui.injectionType.findData(self._data.type))

        self._ui.numberOfParticlesPerPoint.setPFloat(
            self._data.injector.pointInjection.numberOfParticlesPerPoint)
        self._ui.injectionTime.setPFloat(self._data.injector.pointInjection.injectionTime)
        self._ui.pointParticleVelocity.setVector(self._data.injector.pointInjection.particleVelocity)

        self._ui.flowRateSpec.setCurrentIndex(
            self._ui.flowRateSpec.findData(self._data.injector.flowRate.specification))
        self._ui.countParcelPerSecond.setPFloat(
            self._data.injector.flowRate.particleCount.parcelPerSecond)
        self._ui.numberOfParticlesPerParcel.setPFloat(
            self._data.injector.flowRate.particleCount.numberOfParticlesPerParcel)
        self._ui.volumeParcelPerSecond.setPFloat(
            self._data.injector.flowRate.particleVolume.parcelPerSecond)
        self._ui.totalMass.setPFloat(self._data.injector.flowRate.particleVolume.totalMass)
        self._ui.volumeFlowRate.setData(self._data.injector.flowRate.particleVolume.volumeFlowRate)
        self._ui.massFlowRate.setPFloat(self._data.injector.flowRate.particleVolume.massFlowRate)
        self._ui.startTime.setPFloat(self._data.injector.flowRate.startTime)
        self._ui.stopTime.setPFloat(self._data.injector.flowRate.stopTime)

        self._ui.surfaceParticleVelocityType.setCurrentIndex(
            self._ui.surfaceParticleVelocityType.findData(
                self._data.injector.surfaceInjection.particleVelocity.type))
        self._ui.surfaceParticleVelocity.setVector(self._data.injector.surfaceInjection.particleVelocity.value)
        self._setSurface(self._data.injector.surfaceInjection.bcid)

        self._ui.coneInjectorType.setCurrentIndex(
            self._ui.coneInjectorType.findData(self._data.injector.coneInjection.injectorType))
        self._ui.conePosition.setData(self._data.injector.coneInjection.position)
        self._ui.coneAxis.setData(self._data.injector.coneInjection.axis)
        self._ui.outerConeAngle.setData(self._data.injector.coneInjection.outerConeAngle)
        self._ui.innerConeAngle.setData(self._data.injector.coneInjection.innerConeAngle)
        self._ui.outerRadius.setPFloat(self._data.injector.coneInjection.outerRadius)
        self._ui.innerRadius.setPFloat(self._data.injector.coneInjection.innerRadius)
        self._ui.swirlVelocity.setData(self._data.injector.coneInjection.swirlVelocity)
        self._ui.coneParticleSpeed.setCurrentIndex(
            self._ui.coneParticleSpeed.findData(self._data.injector.coneInjection.particleSpeed))
        self._ui.injectionSpeed.setPFloat(self._data.injector.coneInjection.injectionSpeed)
        self._ui.injectorPressure.setData(self._data.injector.coneInjection.injectorPressure)
        self._ui.dischargeCoeff.setData(self._data.injector.coneInjection.dischargeCoeff)

        self._ui.diameterDistribution.setCurrentIndex(
            self._ui.diameterDistribution.findData(self._data.diameterDistribution.type))
        self._ui.diameter.setPFloat(self._data.diameterDistribution.diameter)
        self._ui.minDiameter.setPFloat(self._data.diameterDistribution.minDiameter)
        self._ui.maxDiameter.setPFloat(self._data.diameterDistribution.maxDiameter)
        self._ui.meanDiameter.setPFloat(self._data.diameterDistribution.meanDiameter)
        self._ui.spreadParameter.setPFloat(self._data.diameterDistribution.spreadParameter)
        self._ui.stdDeviation.setPFloat(self._data.diameterDistribution.stdDeviation)

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name == '':
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Injection Name is required.'))
            return

        if name != self._data.name and name in self._usedNames:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Injection Name "{}" is already used.').format(name))
            return

        try:
            data = copy.deepcopy(self._data)
            data.name = name

            injectionType = self._ui.injectionType.currentData()
            data.type = injectionType
            if injectionType == DPMInjectionType.POINT:
                data.injector.pointInjection.numberOfParticlesPerPoint = self._ui.numberOfParticlesPerPoint.pFloat(
                    self.tr('Number of Particles per Point'))
                data.injector.pointInjection.injectionTime = self._ui.injectionTime.pFloat(
                    self.tr('Injection Time'), low=0, lowInclusive=True)
                data.injector.pointInjection.particleVelocity = self._ui.pointParticleVelocity.vector(
                    self.tr('Particle Velocity'))
                if self._positions is not None:  # is edited
                    data.injector.pointInjection.positions = self._positions
            else:
                flowRateSpec = self._ui.flowRateSpec.currentData()
                data.injector.flowRate.specification = flowRateSpec
                if flowRateSpec == DPMFlowRateSpec.PARTICLE_COUNT:
                    data.injector.flowRate.particleCount.parcelPerSecond = self._ui.countParcelPerSecond.pFloat(
                        self.tr('Parcels per Second'), low=0, lowInclusive=False)
                    data.injector.flowRate.particleCount.numberOfParticlesPerParcel = self._ui.numberOfParticlesPerParcel.pFloat(
                        self.tr('Number of Particles per Parcel'), low=0, lowInclusive=False)
                elif flowRateSpec == DPMFlowRateSpec.PARTICLE_VOLUME:
                    data.injector.flowRate.particleVolume.parcelPerSecond = self._ui.volumeParcelPerSecond.pFloat(
                        self.tr('Parcels per Second'), low=0, lowInclusive=False)
                    data.injector.flowRate.particleVolume.totalMass = self._ui.totalMass.pFloat(
                        self.tr('Total Mass'), low=0, lowInclusive=False)
                    data.injector.flowRate.particleVolume.volumeFlowRate = self._ui.volumeFlowRate.data(
                        self.tr('Volume FlowRate'), low=0)
                    data.injector.flowRate.particleVolume.massFlowRate = self._ui.massFlowRate.pFloat(
                        self.tr('Mass Flow Rate'), low=0, lowInclusive=False)

                startTime = self._ui.startTime.pFloat(self.tr('Start Time'), low=0, lowInclusive=True)
                stopTime = self._ui.stopTime.pFloat(self.tr('Stop Time'))
                if startTime >= stopTime:
                    await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                        self.tr('Stop Time must be greater than Start Time.'))
                    return

                data.injector.flowRate.startTime = startTime
                data.injector.flowRate.stopTime = stopTime

                if injectionType == DPMInjectionType.SURFACE:
                    if self._surface == '0':
                        await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Surface.'))
                        return

                    data.injector.surfaceInjection.particleVelocity.type = self._ui.surfaceParticleVelocityType.currentData()
                    data.injector.surfaceInjection.particleVelocity.value = self._ui.surfaceParticleVelocity.vector(
                        self.tr('Particle Velocity'))
                    data.injector.surfaceInjection.bcid = self._surface
                elif injectionType == DPMInjectionType.CONE:
                    coneInjectorType = self._ui.coneInjectorType.currentData()
                    data.injector.coneInjection.injectorType = coneInjectorType
                    data.injector.coneInjection.position = self._ui.conePosition.data(self.tr('Position'))
                    data.injector.coneInjection.axis = self._ui.coneAxis.data(self.tr('Axis'))
                    data.injector.coneInjection.outerConeAngle = self._ui.outerConeAngle.data(
                        self.tr('Outer Cone Angle'), low=0)
                    data.injector.coneInjection.innerConeAngle = self._ui.innerConeAngle.data(
                        self.tr('Inner Cone Angle'), low=0)

                    if coneInjectorType == DPMConeInjectorType.DISC:
                        outerRadius = self._ui.outerRadius.pFloat(self.tr('Outer Radius'))
                        innerRadius = self._ui.innerRadius.pFloat(self.tr('Inner Radius'), low=0)
                        if outerRadius < innerRadius:
                            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                                self.tr('Inner Radius must be less than Outer Radius.'))
                            return

                        data.injector.coneInjection.outerRadius = outerRadius
                        data.injector.coneInjection.innerRadius = innerRadius

                    data.injector.coneInjection.swirlVelocity = self._ui.swirlVelocity.data(
                        self.tr('Swirl Velocity'), low=0)

                    coneParticleSpeed = self._ui.coneParticleSpeed.currentData()
                    data.injector.coneInjection.particleSpeed = coneParticleSpeed
                    if coneParticleSpeed == DPMParticleSpeed.FROM_INJECTION_SPEED:
                        data.injector.coneInjection.injectionSpeed= self._ui.injectionSpeed.pFloat(
                            self.tr('Injection Speed'), low=0)
                    elif coneParticleSpeed == DPMParticleSpeed.FROM_PRESSURE:
                        data.injector.coneInjection.injectorPressure = self._ui.injectorPressure.data(
                            self.tr('Injection Pressure'), low=0)
                    elif coneParticleSpeed == DPMParticleSpeed.FROM_DISCHARGE_COEFF:
                        data.injector.coneInjection.dischargeCoeff = self._ui.dischargeCoeff.data(
                            self.tr('Discharge Coeff'), low=0)

            diameterDistribution = self._ui.diameterDistribution.currentData()
            data.diameterDistribution.type = diameterDistribution
            if diameterDistribution == DPMDiameterDistribution.UNIFORM:
                data.diameterDistribution.diameter = self._ui.diameter.pFloat(
                    self.tr('Diameter'), low=0, lowInclusive=False)
            else:
                minDiameter = self._ui.minDiameter.pFloat(self.tr('Min. Diameter'), low=0, lowInclusive=False)
                maxDiameter = self._ui.maxDiameter.pFloat(self.tr('Max. Diameter'))
                if minDiameter > maxDiameter:
                    await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                        self.tr('Max. Diameter must be greater than Min. Diameter.'))
                    return

                data.diameterDistribution.minDiameter = minDiameter
                data.diameterDistribution.maxDiameter = maxDiameter

                if diameterDistribution != DPMDiameterDistribution.LINEAR:
                    data.diameterDistribution.meanDiameter = self._ui.meanDiameter.pFloat(
                        self.tr('Mean Diameter'))
                    if diameterDistribution in (
                            DPMDiameterDistribution.ROSIN_RAMMLER, DPMDiameterDistribution.MASS_ROSIN_RAMMLER):
                        data.diameterDistribution.spreadParameter = self._ui.spreadParameter.pFloat(
                            self.tr('Spread Parameter'), low=0, lowInclusive=False)
                    elif diameterDistribution == DPMDiameterDistribution.NORMAL:
                        data.diameterDistribution.stdDeviation = self._ui.stdDeviation.pFloat(
                            self.tr('Std. Deviation'), low=0, lowInclusive=False)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.dataAccepted.emit(data)
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
    async def _openPositionEditor(self):
        if self._positions is None:
            self._positions = self._data.injector.pointInjection.positions

        dialog = SimpleSheetDialog(
            self, self.tr('Injection Positions'), ['x', 'y', 'z'],
            [[float(row.x), float(row.y), float(row.z)] for row in self._positions])
        try:
            self._positions = [Vector(PFloat(str(x)), PFloat(str(y)), PFloat(str(z))) for x, y, z in await dialog.show()]
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
