#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from lxml import etree

from baramFlow.base.base import BatchableNumber, Vector, Function1Scalar, Function1Vector
from baramFlow.base.boundary.boundary import PatchInteractionType
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryType
from baramFlow.coredb.libdb import nsmap, dbTextToBool, boolToDBText, ns
from .model import MODELS_XPATH, DPMParticleType, DPMTrackingScheme, DPMDragForce, DPMLiftForce, Contamination
from .model import DPMTurbulentDispersion, DPMHeatTransferSpeicification, DPMEvaporationModel, DPMEnthalpyTransferType
from .model import DPMInjectionType, DPMDiameterDistribution, DPMFlowRateSpec, DPMParticleSpeed, DPMParticleVelocityType
from .model import DPMConeInjectorType

DPM_MODELS_XPATH = f'{MODELS_XPATH}/DPMModels'


@dataclass
class InertProperties:
    inertParticle: str

    @staticmethod
    def fromElement(e):
        return InertProperties(inertParticle=e.find('inertParticle', namespaces=nsmap).text)


@dataclass
class DropletCompositionMaterial:
    mid: str
    composition: str

    @staticmethod
    def fromElement(e):
        return DropletCompositionMaterial(mid=e.find('mid', namespaces=nsmap).text,
                                          composition=e.find('composition', namespaces=nsmap).text)

    def toXML(self):
        return f'<mid>{self.mid}</mid><composition>{self.composition}</composition>'


@dataclass
class DropletProperties:
    composition: list
    temperature: BatchableNumber

    @staticmethod
    def fromElement(e):
        composition = []
        for material in e.findall('composition/material', namespaces=nsmap):
            composition.append(DropletCompositionMaterial.fromElement(material))

        return DropletProperties(composition=composition,
                                 temperature=BatchableNumber.fromElement(e.find('temperature', namespaces=nsmap)))


@dataclass
class NumericalConditions:
    interactionWithContinuousPhase: bool
    maxParticleCourantNumber: BatchableNumber
    DPMIterationInterval: BatchableNumber
    nodeBasedAveraging: bool
    trackingScheme: DPMTrackingScheme

    @staticmethod
    def fromElement(e):
        return NumericalConditions(
            interactionWithContinuousPhase=dbTextToBool(e.find('interactionWithContinuousPhase', namespaces=nsmap).text),
            maxParticleCourantNumber=BatchableNumber.fromElement(e.find('maxParticleCourantNumber', namespaces=nsmap)),
            DPMIterationInterval=BatchableNumber.fromElement(e.find('DPMIterationInterval', namespaces=nsmap)),
            nodeBasedAveraging=dbTextToBool(e.find('nodeBasedAveraging', namespaces=nsmap).text),
            trackingScheme=DPMTrackingScheme(e.find('trackingScheme', namespaces=nsmap).text))


@dataclass
class NonSphereDrag:
    shapeFactor: BatchableNumber

    @staticmethod
    def fromElement(e):
        return NonSphereDrag(
            shapeFactor=BatchableNumber.fromElement(e.find('shapeFactor', namespaces=nsmap)))


@dataclass
class TomiyamaDrag:
    surfaceTension: BatchableNumber
    contamination: Contamination

    @staticmethod
    def fromElement(e):
        return TomiyamaDrag(
            surfaceTension=BatchableNumber.fromElement(e.find('surfaceTension', namespaces=nsmap)),
            contamination=Contamination(e.find('contamination', namespaces=nsmap).text))


@dataclass
class DragForce:
    specification: DPMDragForce
    nonSphereDrag: NonSphereDrag
    tomyamaDrag: TomiyamaDrag

    @staticmethod
    def fromElement(e):
        return DragForce(
            specification=DPMDragForce(e.find('specification', namespaces=nsmap).text),
            nonSphereDrag=NonSphereDrag.fromElement(e.find('nonSphereDrag', namespaces=nsmap)),
            tomyamaDrag=TomiyamaDrag.fromElement(e.find('TomiyamaDrag', namespaces=nsmap)))


@dataclass
class TomiyamaLift:
    surfaceTension: BatchableNumber

    @staticmethod
    def fromElement(e):
        return TomiyamaLift(
            surfaceTension=BatchableNumber.fromElement(e.find('surfaceTension', namespaces=nsmap)))


@dataclass
class LiftForce:
    specification: DPMLiftForce
    tomiyamaLift: TomiyamaLift

    @staticmethod
    def fromElement(e):
        return LiftForce(
            specification=DPMLiftForce(e.find('specification', namespaces=nsmap).text),
            tomiyamaLift=TomiyamaLift.fromElement(e.find('TomiyamaLift', namespaces=nsmap)))


@dataclass
class BrownianMotionForce:
    disabled: bool
    molecularFreePathLength: BatchableNumber
    useTurbulence: bool

    @staticmethod
    def fromElement(e):
        return BrownianMotionForce(
            disabled=dbTextToBool(e.get('disabled')),
            molecularFreePathLength=BatchableNumber.fromElement(e.find('molecularFreePathLength', namespaces=nsmap)),
            useTurbulence=dbTextToBool(e.find('useTurbulence', namespaces=nsmap).text))


@dataclass
class KinematicModel:
    dragForce: DragForce
    liftForce: LiftForce
    gravity: bool
    pressureGradient: bool
    brownianMotionForce: BrownianMotionForce

    @staticmethod
    def fromElement(e):
        return KinematicModel(
            dragForce=DragForce.fromElement(e.find('dragForce', namespaces=nsmap)),
            liftForce=LiftForce.fromElement(e.find('liftForce', namespaces=nsmap)),
            gravity=dbTextToBool(e.find('gravity', namespaces=nsmap).text),
            pressureGradient=dbTextToBool(e.find('pressureGradient', namespaces=nsmap).text),
            brownianMotionForce=BrownianMotionForce.fromElement(e.find('brownianMotionForce', namespaces=nsmap)))


@dataclass
class RanzMarshall:
    birdCorrection: bool

    @staticmethod
    def fromElement(e):
        return RanzMarshall(birdCorrection=dbTextToBool(e.find('birdCorrection', namespaces=nsmap).text))


@dataclass
class HeatTransfer:
    specification: DPMHeatTransferSpeicification
    ranzMarsahll: RanzMarshall

    @staticmethod
    def fromElement(e):
        return HeatTransfer(specification=DPMHeatTransferSpeicification(e.find('specification', namespaces=nsmap).text),
                            ranzMarsahll=RanzMarshall.fromElement(e.find('ranzMarshall', namespaces=nsmap)))


@dataclass
class Evaporation:
    model: DPMEvaporationModel
    enthalpyTransferType: DPMEnthalpyTransferType

    @staticmethod
    def fromElement(e):
        return Evaporation(
            model=DPMEvaporationModel(e.find('model', namespaces=nsmap).text),
            enthalpyTransferType=DPMEnthalpyTransferType(e.find('enthalpyTransferType', namespaces=nsmap).text))


@dataclass
class DPMModelProperties:
    particleType: DPMParticleType
    inert: InertProperties
    droplet: DropletProperties
    numericalConditions: NumericalConditions
    kinematicModel: KinematicModel
    turbulentDispersion: DPMTurbulentDispersion
    heatTransfer: HeatTransfer
    evaporation: Evaporation

    @staticmethod
    def fromElement(e):
        return DPMModelProperties(
            particleType=DPMParticleType(e.find('particleType', namespaces=nsmap).text),
            inert=InertProperties.fromElement(e.find('inert', namespaces=nsmap)),
            droplet=DropletProperties.fromElement(e.find('droplet', namespaces=nsmap)),
            numericalConditions=NumericalConditions.fromElement(e.find('numericalConditions', namespaces=nsmap)),
            kinematicModel=KinematicModel.fromElement(e.find('kinematicModel', namespaces=nsmap)),
            turbulentDispersion=DPMTurbulentDispersion(e.find('turbulentDispersion', namespaces=nsmap).text),
            heatTransfer=HeatTransfer.fromElement(e.find('heatTransfer', namespaces=nsmap)),
            evaporation=Evaporation.fromElement(e.find('evaporation', namespaces=nsmap)),
        )

    def toElement(self):
        composition = ''
        for item in self.droplet.composition:
            composition += f'<material>{item.toXML()}</material>'

        return etree.fromstring(
            f'''
            <properties xmlns="http://www.baramcfd.org/baram">
                <particleType>{self.particleType.value}</particleType>
                <inert>
                    <inertParticle>{self.inert.inertParticle}</inertParticle>
                </inert>
                <droplet>
                    <composition>{composition}</composition>
                    {self.droplet.temperature.toXML('temperature')}
                </droplet>
                <numericalConditions>
                    <interactionWithContinuousPhase>{boolToDBText(self.numericalConditions.interactionWithContinuousPhase)}</interactionWithContinuousPhase>
                    {self.numericalConditions.maxParticleCourantNumber.toXML('maxParticleCourantNumber')}
                    {self.numericalConditions.DPMIterationInterval.toXML('DPMIterationInterval')}
                    <nodeBasedAveraging>{boolToDBText(self.numericalConditions.nodeBasedAveraging)}</nodeBasedAveraging>
                    <trackingScheme>{self.numericalConditions.trackingScheme.value}</trackingScheme>
                </numericalConditions>
                <kinematicModel>
                    <dragForce>
                        <specification>{self.kinematicModel.dragForce.specification.value}</specification>
                        <nonSphereDrag>
                            {self.kinematicModel.dragForce.nonSphereDrag.shapeFactor.toXML('shapeFactor')}
                        </nonSphereDrag>
                        <TomiyamaDrag>
                            {self.kinematicModel.dragForce.tomyamaDrag.surfaceTension.toXML('surfaceTension')}
                            <contamination>{self.kinematicModel.dragForce.tomyamaDrag.contamination.value}</contamination>
                        </TomiyamaDrag>
                    </dragForce>
                    <liftForce>
                        <specification>{self.kinematicModel.liftForce.specification.value}</specification>
                        <TomiyamaLift>
                            {self.kinematicModel.liftForce.tomiyamaLift.surfaceTension.toXML('surfaceTension')}
                        </TomiyamaLift>
                    </liftForce>
                    <gravity>{boolToDBText(self.kinematicModel.gravity)}</gravity>
                    <pressureGradient>{boolToDBText(self.kinematicModel.pressureGradient)}</pressureGradient>
                    <brownianMotionForce{' disabled="true"' if self.kinematicModel.brownianMotionForce.disabled else ''}>
                        {self.kinematicModel.brownianMotionForce.molecularFreePathLength.toXML('molecularFreePathLength')}
                        <useTurbulence>{boolToDBText(self.kinematicModel.brownianMotionForce.useTurbulence)}</useTurbulence>
                    </brownianMotionForce>
                </kinematicModel>
                <turbulentDispersion>{self.turbulentDispersion.value}</turbulentDispersion>
                <heatTransfer>
                    <specification>{self.heatTransfer.specification.value}</specification>
                    <ranzMarshall>
                        <birdCorrection>{boolToDBText(self.heatTransfer.ranzMarsahll.birdCorrection)}</birdCorrection>
                    </ranzMarshall>
                </heatTransfer>
                <evaporation>
                    <model>{self.evaporation.model.value}</model>
                    <enthalpyTransferType>{self.evaporation.enthalpyTransferType.value}</enthalpyTransferType>
                </evaporation>
            </properties>
            '''
        )


@dataclass
class PointInjection:
    numberOfParticlesPerPoint: BatchableNumber  = field(default_factory=lambda: BatchableNumber('100'))
    injectionTime: BatchableNumber              = field(default_factory=lambda: BatchableNumber('0'))
    particleVelocity: Vector                    = field(default_factory=lambda: Vector.new('1', '1', '1'))
    positions: list                             = field(default_factory=list)

    @staticmethod
    def fromElement(e):
        positions = []
        for p in e.findall('positions/position', namespaces=nsmap):
            positions.append(Vector.fromElement(p))

        return PointInjection(
            numberOfParticlesPerPoint=BatchableNumber.fromElement(e.find('numberOfParticlesPerPoint', namespaces=nsmap)),
            injectionTime=BatchableNumber.fromElement(e.find('injectionTime', namespaces=nsmap)),
            particleVelocity=Vector.fromElement(e.find('particleVelocity', namespaces=nsmap)),
            positions=positions
        )


@dataclass
class ParticleCountParameters:
    parcelPerSecond: BatchableNumber            = field(default_factory=lambda: BatchableNumber('100'))
    numberOfParticlesPerParcel: BatchableNumber = field(default_factory=lambda: BatchableNumber('100'))

    @staticmethod
    def fromElement(e):
        return ParticleCountParameters(
            parcelPerSecond=BatchableNumber.fromElement(e.find('parcelPerSecond', namespaces=nsmap)),
            numberOfParticlesPerParcel=BatchableNumber.fromElement(
                e.find('numberOfParticlesPerParcel',namespaces=nsmap)))


@dataclass
class ParticleVolumeParameters:
    parcelPerSecond: BatchableNumber    = field(default_factory=lambda: BatchableNumber('100'))
    totalMass: BatchableNumber          = field(default_factory=lambda: BatchableNumber('100'))
    volumeFlowRate: Function1Scalar     = field(default_factory=lambda: Function1Scalar(constant=BatchableNumber('100')))
    massFlowRate: BatchableNumber       = field(default_factory=lambda: BatchableNumber('100'))

    @staticmethod
    def fromElement(e):
        return ParticleVolumeParameters(
            parcelPerSecond=BatchableNumber.fromElement(e.find('parcelPerSecond', namespaces=nsmap)),
            totalMass=BatchableNumber.fromElement(e.find('totalMass',namespaces=nsmap)),
            volumeFlowRate=Function1Scalar.fromElement(e.find('volumeFlowRate',namespaces=nsmap)),
            massFlowRate=BatchableNumber.fromElement(e.find('massFlowRate',namespaces=nsmap)))


@dataclass
class FlowRate:
    specification: DPMFlowRateSpec              = DPMFlowRateSpec.PARTICLE_COUNT
    particleCount: ParticleCountParameters      = field(default_factory=ParticleCountParameters)
    particleVolume: ParticleVolumeParameters    = field(default_factory=ParticleVolumeParameters)
    startTime: BatchableNumber                  = field(default_factory=lambda: BatchableNumber('0'))
    stopTime: BatchableNumber                   = field(default_factory=lambda: BatchableNumber('1'))

    @staticmethod
    def fromElement(e):
        return FlowRate(
            specification=DPMFlowRateSpec(e.find('specification', namespaces=nsmap).text),
            particleCount=ParticleCountParameters.fromElement(e.find('particleCount', namespaces=nsmap)),
            particleVolume=ParticleVolumeParameters.fromElement(e.find('particleVolume', namespaces=nsmap)),
            startTime=BatchableNumber.fromElement(e.find('startTime', namespaces=nsmap)),
            stopTime=BatchableNumber.fromElement(e.find('stopTime', namespaces=nsmap)))


@dataclass
class ConeInjection:
    injectorType: DPMConeInjectorType   = DPMConeInjectorType.DISC
    position: Function1Vector           = field(default_factory=lambda: Function1Vector(constant=Vector.new('1', '1', '1')))
    axis: Function1Vector               = field(default_factory=lambda: Function1Vector(constant=Vector.new('1', '1', '1')))
    outerConeAngle: Function1Scalar     = field(default_factory=lambda: Function1Scalar(constant=BatchableNumber('30')))
    innerConeAngle: Function1Scalar     = field(default_factory=lambda: Function1Scalar(constant=BatchableNumber('0')))
    outerRadius: BatchableNumber        = field(default_factory=lambda: BatchableNumber('1'))
    innerRadius: BatchableNumber        = field(default_factory=lambda: BatchableNumber('0'))
    swirlVelocity: Function1Scalar      = field(default_factory=lambda: Function1Scalar(constant=BatchableNumber('0')))
    particleSpeed: DPMParticleSpeed     = DPMParticleSpeed.FROM_INJECTION_SPEED
    injectionSpeed: BatchableNumber     = field(default_factory=lambda: BatchableNumber('1'))
    injectorPressure: Function1Scalar   = field(default_factory=lambda: Function1Scalar(constant=BatchableNumber('0')))
    dischargeCoeff: Function1Scalar     = field(default_factory=lambda: Function1Scalar(constant=BatchableNumber('0')))

    @staticmethod
    def fromElement(e):
        return ConeInjection(
            injectorType=DPMConeInjectorType(e.find('injectorType', namespaces=nsmap).text),
            position=Function1Vector.fromElement(e.find('position', namespaces=nsmap)),
            axis=Function1Vector.fromElement(e.find('axis', namespaces=nsmap)),
            outerConeAngle=Function1Scalar.fromElement(e.find('outerConeAngle', namespaces=nsmap)),
            innerConeAngle=Function1Scalar.fromElement(e.find('innerConeAngle', namespaces=nsmap)),
            outerRadius=BatchableNumber.fromElement(e.find('outerRadius', namespaces=nsmap)),
            innerRadius=BatchableNumber.fromElement(e.find('innerRadius', namespaces=nsmap)),
            swirlVelocity=Function1Scalar.fromElement(e.find('swirlVelocity', namespaces=nsmap)),
            particleSpeed=DPMParticleSpeed(e.find('particleSpeed', namespaces=nsmap).text),
            injectionSpeed=BatchableNumber.fromElement(e.find('injectionSpeed', namespaces=nsmap)),
            injectorPressure=Function1Scalar.fromElement(e.find('injectorPressure', namespaces=nsmap)),
            dischargeCoeff=Function1Scalar.fromElement(e.find('dischargeCoeff', namespaces=nsmap)))


@dataclass
class ParticleVelocity:
    type: DPMParticleVelocityType   = DPMParticleVelocityType.CONSTANT
    value: Vector                   = field(default_factory=lambda: Vector.new('1', '1', '1'))

    @staticmethod
    def fromElement(e):
        return ParticleVelocity(type=DPMParticleVelocityType(e.find('type', namespaces=nsmap).text),
                                value=Vector.fromElement(e.find('value', namespaces=nsmap)))


@dataclass
class SurfaceInjection:
    particleVelocity: ParticleVelocity  = field(default_factory=ParticleVelocity)
    bcid: str                           = '0'

    @staticmethod
    def fromElement(e):
        return SurfaceInjection(
            particleVelocity=ParticleVelocity.fromElement(e.find('particleVelocity', namespaces=nsmap)),
            bcid=e.find('surface', namespaces=nsmap).text)


@dataclass
class Injector:
    type: DPMInjectionType              = DPMInjectionType.CONE
    pointInjection: PointInjection      = field(default_factory=PointInjection)
    flowRate: FlowRate                  = field(default_factory=FlowRate)
    surfaceInjection: SurfaceInjection  = field(default_factory=SurfaceInjection)
    coneInjection: ConeInjection        = field(default_factory=ConeInjection)

    @staticmethod
    def fromElement(e):
        properties = e.find('injectorProperties', namespaces=nsmap)
        return Injector(type=DPMInjectionType(e.find('type', namespaces=nsmap).text),
                        pointInjection=PointInjection.fromElement(properties.find('pointInjection', namespaces=nsmap)),
                        flowRate=FlowRate.fromElement(properties.find('flowRate', namespaces=nsmap)),
                        surfaceInjection=SurfaceInjection.fromElement(
                            properties.find('surfaceInjection', namespaces=nsmap)),
                        coneInjection=ConeInjection.fromElement(properties.find('coneInjection', namespaces=nsmap)))


@dataclass
class DiameterDistribution:
    type: DPMDiameterDistribution       = DPMDiameterDistribution.UNIFORM
    diameter: BatchableNumber           = field(default_factory=lambda: BatchableNumber('0.0001'))
    minDiameter: BatchableNumber        = field(default_factory=lambda: BatchableNumber('0.0001'))
    maxDiameter: BatchableNumber        = field(default_factory=lambda: BatchableNumber('0.0001'))
    meanDiameter: BatchableNumber       = field(default_factory=lambda: BatchableNumber('0.0001'))
    spreadParameter: BatchableNumber    = field(default_factory=lambda: BatchableNumber('0.0001'))
    stdDeviation: BatchableNumber       = field(default_factory=lambda: BatchableNumber('0.0001'))

    @staticmethod
    def fromElement(e):
        return DiameterDistribution(
            type=DPMDiameterDistribution(e.find('type', namespaces=nsmap).text),
            diameter=BatchableNumber.fromElement(e.find('diameter', namespaces=nsmap)),
            minDiameter=BatchableNumber.fromElement(e.find('minDiameter', namespaces=nsmap)),
            maxDiameter=BatchableNumber.fromElement(e.find('maxDiameter', namespaces=nsmap)),
            meanDiameter=BatchableNumber.fromElement(e.find('meanDiameter', namespaces=nsmap)),
            spreadParameter=BatchableNumber.fromElement(e.find('spreadParameter', namespaces=nsmap)),
            stdDeviation=BatchableNumber.fromElement(e.find('stdDeviation', namespaces=nsmap)))


@dataclass
class Injection:
    name: str                                   = ''
    injector: Injector                          = field(default_factory=Injector)
    diameterDistribution: DiameterDistribution  = field(default_factory=DiameterDistribution)

    @staticmethod
    def new():
        return Injection.fromElement(
            etree.fromstring(
                '''
                <injection xmlns="http://www.baramcfd.org/baram">
                    <name></name>
                    <type>cone</type>
                    <injectorProperties>
                        <pointInjection>
                            <numberOfParticlesPerPoint>100</numberOfParticlesPerPoint>
                            <injectionTime>0</injectionTime>
                            <particleVelocity>
                                <x>1</x>
                                <y>1</y>
                                <z>1</z>
                            </particleVelocity>
                            <positions/>
                        </pointInjection>
                        <flowRate>
                            <specification>particleCount</specification>
                            <particleCount>
                                <parcelPerSecond>100</parcelPerSecond>
                                <numberOfParticlesPerParcel>100</numberOfParticlesPerParcel>
                            </particleCount>
                            <particleVolume>
                                <parcelPerSecond>100</parcelPerSecond>
                                <totalMass>1e-6</totalMass>
                                <volumeFlowRate>
                                    <type>constant</type>
                                    <constant>1e-6</constant>
                                </volumeFlowRate>
                                <massFlowRate>1e-6</massFlowRate>
                            </particleVolume>
                            <startTime>0</startTime>
                            <stopTime>1</stopTime>
                        </flowRate>
                        <coneInjection>
                            <injectorType>disc</injectorType>
                            <position>
                                <type>constant</type>
                                <constant>
                                    <x>1</x>
                                    <y>1</y>
                                    <z>1</z>
                                </constant>
                            </position>
                            <axis>
                                <type>constant</type>
                                <constant>
                                    <x>1</x>
                                    <y>1</y>
                                    <z>1</z>
                                </constant>
                            </axis>
                            <outerConeAngle>
                                <type>constant</type>
                                <constant>30</constant>
                            </outerConeAngle>
                            <innerConeAngle>
                                <type>constant</type>
                                <constant>0</constant>
                            </innerConeAngle>
                            <outerRadius>1</outerRadius>
                            <innerRadius>0</innerRadius>
                            <swirlVelocity>
                                <type>constant</type>
                                <constant>0</constant>
                            </swirlVelocity>
                            <particleSpeed>fromInjectionSpeed</particleSpeed>
                            <injectionSpeed>1</injectionSpeed>
                            <injectorPressure>
                                <type>constant</type>
                                <constant>0</constant>
                            </injectorPressure>
                            <dischargeCoeff>
                                <type>constant</type>
                                <constant>0</constant>
                            </dischargeCoeff>
                        </coneInjection>
                        <surfaceInjection>
                            <particleVelocity>
                                <type>constant</type>
                                <value>
                                    <x>1</x>
                                    <y>1</y>
                                    <z>1</z>
                                </value>
                            </particleVelocity>
                            <surface>0</surface>
                        </surfaceInjection>
                    </injectorProperties>
                    <diameterDistribution>
                        <type>uniform</type>
                        <diameter>0.0001</diameter>
                        <minDiameter>0.0001</minDiameter>
                        <maxDiameter>0.0001</maxDiameter>
                        <meanDiameter>0.0001</meanDiameter>
                        <spreadParameter>0.0001</spreadParameter>
                        <stdDeviation>0.0001</stdDeviation>
                    </diameterDistribution>
                </injection>
                '''
            ))

    @staticmethod
    def fromElement(e):
        return Injection(
            name=e.find('name', namespaces=nsmap).text,
            injector=Injector.fromElement(e),
            diameterDistribution=DiameterDistribution.fromElement(e.find('diameterDistribution', namespaces=nsmap)))

    def toElement(self):
        positions = ''
        for position in self.injector.pointInjection.positions:
            positions += f'<position>{position.toXML()}</position>'

        return etree.fromstring(
            f'''
            <injection xmlns="http://www.baramcfd.org/baram">
                <name>{self.name}</name>
                <type>{self.injector.type.value}</type>
                <injectorProperties>
                    <pointInjection>
                        {self.injector.pointInjection.numberOfParticlesPerPoint.toXML('numberOfParticlesPerPoint')}
                        {self.injector.pointInjection.injectionTime.toXML('injectionTime')}
                        <particleVelocity>{self.injector.pointInjection.particleVelocity.toXML()}</particleVelocity>
                        <positions>{positions}</positions>
                    </pointInjection>
                    <flowRate>
                        <specification>{self.injector.flowRate.specification.value}</specification>
                        <particleCount>
                            {self.injector.flowRate.particleCount.parcelPerSecond.toXML('parcelPerSecond')}
                            {self.injector.flowRate.particleCount.numberOfParticlesPerParcel.toXML('numberOfParticlesPerParcel')}
                        </particleCount>
                        <particleVolume>
                            {self.injector.flowRate.particleVolume.parcelPerSecond.toXML('parcelPerSecond')}
                            {self.injector.flowRate.particleVolume.totalMass.toXML('totalMass')}
                            <volumeFlowRate>{self.injector.flowRate.particleVolume.volumeFlowRate.toXML()}</volumeFlowRate>
                            {self.injector.flowRate.particleVolume.massFlowRate.toXML('massFlowRate')}
                        </particleVolume>
                        {self.injector.flowRate.startTime.toXML('startTime')}
                        {self.injector.flowRate.stopTime.toXML('stopTime')}
                    </flowRate>
                    <coneInjection>
                        <injectorType>{self.injector.coneInjection.injectorType.value}</injectorType>
                        <position>{self.injector.coneInjection.position.toXML()}</position>
                        <axis>{self.injector.coneInjection.axis.toXML()}</axis>
                        <outerConeAngle>{self.injector.coneInjection.outerConeAngle.toXML()}</outerConeAngle>
                        <innerConeAngle>{self.injector.coneInjection.innerConeAngle.toXML()}</innerConeAngle>
                        {self.injector.coneInjection.outerRadius.toXML('outerRadius')}
                        {self.injector.coneInjection.innerRadius.toXML('innerRadius')}
                        <swirlVelocity>{self.injector.coneInjection.swirlVelocity.toXML()}</swirlVelocity>
                        <particleSpeed>{self.injector.coneInjection.particleSpeed.value}</particleSpeed>
                        {self.injector.coneInjection.injectionSpeed.toXML('injectionSpeed')}
                        <injectorPressure>{self.injector.coneInjection.injectorPressure.toXML()}</injectorPressure>
                        <dischargeCoeff>{self.injector.coneInjection.dischargeCoeff.toXML()}</dischargeCoeff>
                    </coneInjection>
                    <surfaceInjection>
                        <particleVelocity>
                            <type>{self.injector.surfaceInjection.particleVelocity.type.value}</type>
                            <value>{self.injector.surfaceInjection.particleVelocity.value.toXML()}</value>
                        </particleVelocity>
                        <surface>{self.injector.surfaceInjection.bcid}</surface>
                    </surfaceInjection>
                </injectorProperties>
                <diameterDistribution>
                    <type>{self.diameterDistribution.type.value}</type>
                    {self.diameterDistribution.diameter.toXML('diameter')}
                    {self.diameterDistribution.minDiameter.toXML('minDiameter')}
                    {self.diameterDistribution.maxDiameter.toXML('maxDiameter')}
                    {self.diameterDistribution.meanDiameter.toXML('meanDiameter')}
                    {self.diameterDistribution.spreadParameter.toXML('spreadParameter')}
                    {self.diameterDistribution.stdDeviation.toXML('stdDeviation')}
                </diameterDistribution>
            </injection>
            '''
        )


class DPMModelManager:
    @staticmethod
    def isModelOn():
        return DPMModelManager.particleType() != DPMParticleType.NONE

    @staticmethod
    def particleType():
        return DPMParticleType(coredb.CoreDB().getValue(DPM_MODELS_XPATH + '/properties/particleType'))

    @staticmethod
    def properties():
        return DPMModelProperties.fromElement(coredb.CoreDB().getElement(DPM_MODELS_XPATH + '/properties'))

    @staticmethod
    def injections():
        return [Injection.fromElement(e) for e in coredb.CoreDB().getElement(DPM_MODELS_XPATH + '/injections')]

    @staticmethod
    def inertParticle():
        return coredb.CoreDB().getValue(DPM_MODELS_XPATH + '/properties/inert/inertParticle')

    @staticmethod
    def dropletCompositionMaterials():
        return [e.text
                for e in coredb.CoreDB().getElements(DPM_MODELS_XPATH + '/properties/droplet/composition/material/mid')]

    @staticmethod
    def updateDPMModel(db, properties, injections):
        dpmModels = db.getElement(DPM_MODELS_XPATH)

        if injections is None:  # Not modified
            injectionsElement = dpmModels.find('injections', namespaces=nsmap)
        else:
            injectionsElement = etree.Element(f'{{{ns}}}injections')
            for injection in injections:
                injectionsElement.append(Injection.toElement(injection))

        dpmModels.clear()
        dpmModels.append(properties.toElement())
        dpmModels.append(injectionsElement)

        db.increaseConfigCount()

    @staticmethod
    def turnOff(meshUpdated=False):
        if meshUpdated:
            properties = DPMModelManager.properties()
            properties.particleType = DPMParticleType.NONE
            properties.droplet.composition = []

            DPMModelManager.updateDPMModel(coredb.CoreDB(), properties, [])
        else:
            coredb.CoreDB().setValue(DPM_MODELS_XPATH + '/properties/particleType', DPMParticleType.NONE.value)

    @staticmethod
    def clearDropletComposition(db):
        composition = db.getElement(DPM_MODELS_XPATH + '/properties/droplet/composition')
        composition.clear()

    @staticmethod
    def removeInertParticle(db):
        db.setValue(DPM_MODELS_XPATH + '/properties/inert/inertParticle', '0')

    @staticmethod
    def getDefaultPatchInteractionType(type_: BoundaryType)->PatchInteractionType:
        if type_ in [BoundaryType.WALL,
                     BoundaryType.THERMO_COUPLED_WALL,
                     BoundaryType.SYMMETRY,
                     ]:
            return PatchInteractionType.REFLECT
        elif type_ in [BoundaryType.POROUS_JUMP,
                       BoundaryType.FAN,
                       BoundaryType.INTERFACE,
                       BoundaryType.EMPTY,
                       BoundaryType.WEDGE,
                       ]:
            return PatchInteractionType.NONE
        else:
            return PatchInteractionType.ESCAPE
