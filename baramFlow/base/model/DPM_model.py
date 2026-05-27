#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from lxml import etree

from libbaram.pfloat import PFloat

from baramFlow.base.base import Function1Scalar, Function1Vector, Vector
from baramFlow.base.boundary.boundary import PatchInteractionType
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryType
from baramFlow.coredb.libdb import boolToXml, E, nsmap, xmlToBool
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

    def toElement(self, tag: str):
        return E(tag,
                 E('inertParticle', self.inertParticle))


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

    def toElement(self, tag: str):
        return E(tag,
                 E('mid', self.mid),
                 E('composition', self.composition))

@dataclass
class DropletProperties:
    composition: list[DropletCompositionMaterial]
    temperature: PFloat

    @staticmethod
    def fromElement(e):
        composition = []
        for material in e.findall('composition/material', namespaces=nsmap):
            composition.append(DropletCompositionMaterial.fromElement(material))

        return DropletProperties(composition=composition,
                                 temperature=PFloat.fromElement(e.find('temperature', namespaces=nsmap)))

    def toElement(self, tag: str):
        compositionElement =  E('composition')
        compositionElement.extend([c.toElement('material') for c in self.composition])
        return E(tag,
                 compositionElement,
                 self.temperature.toElement('temperature'))

@dataclass
class NumericalConditions:
    interactionWithContinuousPhase: bool
    maxParticleCourantNumber: PFloat
    DPMIterationInterval: PFloat
    nodeBasedAveraging: bool
    trackingScheme: DPMTrackingScheme

    @staticmethod
    def fromElement(e):
        return NumericalConditions(
            interactionWithContinuousPhase=xmlToBool(e.find('interactionWithContinuousPhase', namespaces=nsmap).text),
            maxParticleCourantNumber=PFloat.fromElement(e.find('maxParticleCourantNumber', namespaces=nsmap)),
            DPMIterationInterval=PFloat.fromElement(e.find('DPMIterationInterval', namespaces=nsmap)),
            nodeBasedAveraging=xmlToBool(e.find('nodeBasedAveraging', namespaces=nsmap).text),
            trackingScheme=DPMTrackingScheme(e.find('trackingScheme', namespaces=nsmap).text))

    def toElement(self, tag: str):
        return E(tag,
                 E('interactionWithContinuousPhase', self.interactionWithContinuousPhase),
                 self.maxParticleCourantNumber.toElement('maxParticleCourantNumber'),
                 self.DPMIterationInterval.toElement('DPMIterationInterval'),
                 E('nodeBasedAveraging', self.interactionWithContinuousPhase),
                 self.trackingScheme.toElement('trackingScheme'))

@dataclass
class NonSphereDrag:
    shapeFactor: PFloat

    @staticmethod
    def fromElement(e):
        return NonSphereDrag(
            shapeFactor=PFloat.fromElement(e.find('shapeFactor', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.shapeFactor.toElement('shapeFactor'))

@dataclass
class TomiyamaDrag:
    surfaceTension: PFloat
    contamination: Contamination

    @staticmethod
    def fromElement(e):
        return TomiyamaDrag(
            surfaceTension=PFloat.fromElement(e.find('surfaceTension', namespaces=nsmap)),
            contamination=Contamination(e.find('contamination', namespaces=nsmap).text))

    def toElement(self, tag: str):
        return E(tag,
                 self.surfaceTension.toElement('surfaceTension'),
                 self.contamination.toElement('contamination'))

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

    def toElement(self, tag: str):
        return E(tag,
                 self.specification.toElement('specification'),
                 self.nonSphereDrag.toElement('nonSphereDrag'),
                 self.tomyamaDrag.toElement('TomiyamaDrag'))

@dataclass
class TomiyamaLift:
    surfaceTension: PFloat

    @staticmethod
    def fromElement(e):
        return TomiyamaLift(
            surfaceTension=PFloat.fromElement(e.find('surfaceTension', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.surfaceTension.toElement('surfaceTension'))

@dataclass
class LiftForce:
    specification: DPMLiftForce
    tomiyamaLift: TomiyamaLift

    @staticmethod
    def fromElement(e):
        return LiftForce(
            specification=DPMLiftForce(e.find('specification', namespaces=nsmap).text),
            tomiyamaLift=TomiyamaLift.fromElement(e.find('TomiyamaLift', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.specification.toElement('specification'),
                 self.tomiyamaLift.toElement('TomiyamaLift'))

@dataclass
class BrownianMotionForce:
    disabled: bool
    molecularFreePathLength: PFloat
    useTurbulence: bool

    @staticmethod
    def fromElement(e):
        return BrownianMotionForce(
            disabled=xmlToBool(e.get('disabled')),
            molecularFreePathLength=PFloat.fromElement(e.find('molecularFreePathLength', namespaces=nsmap)),
            useTurbulence=xmlToBool(e.find('useTurbulence', namespaces=nsmap).text))

    def toElement(self, tag: str):
        return E(tag,
                 self.molecularFreePathLength.toElement('molecularFreePathLength'),
                 E('useTurbulence', self.useTurbulence),
                 disabled=boolToXml(self.disabled))

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
            gravity=xmlToBool(e.find('gravity', namespaces=nsmap).text),
            pressureGradient=xmlToBool(e.find('pressureGradient', namespaces=nsmap).text),
            brownianMotionForce=BrownianMotionForce.fromElement(e.find('brownianMotionForce', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.dragForce.toElement('dragForce'),
                 self.liftForce.toElement('liftForce'),
                 E('gravity', self.gravity),
                 E('pressureGradient', self.pressureGradient),
                 self.brownianMotionForce.toElement('brownianMotionForce'))

@dataclass
class RanzMarshall:
    birdCorrection: bool

    @staticmethod
    def fromElement(e):
        return RanzMarshall(birdCorrection=xmlToBool(e.find('birdCorrection', namespaces=nsmap).text))

    def toElement(self, tag: str):
        return E(tag,
                 E('birdCorrection', self.birdCorrection))

@dataclass
class HeatTransfer:
    specification: DPMHeatTransferSpeicification
    ranzMarsahll: RanzMarshall

    @staticmethod
    def fromElement(e):
        return HeatTransfer(specification=DPMHeatTransferSpeicification(e.find('specification', namespaces=nsmap).text),
                            ranzMarsahll=RanzMarshall.fromElement(e.find('ranzMarshall', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.specification.toElement('specification'),
                 self.ranzMarsahll.toElement('ranzMarshall'))

@dataclass
class Evaporation:
    model: DPMEvaporationModel
    enthalpyTransferType: DPMEnthalpyTransferType

    @staticmethod
    def fromElement(e):
        return Evaporation(
            model=DPMEvaporationModel(e.find('model', namespaces=nsmap).text),
            enthalpyTransferType=DPMEnthalpyTransferType(e.find('enthalpyTransferType', namespaces=nsmap).text))

    def toElement(self, tag: str):
        return E(tag,
                 self.model.toElement('model'),
                 self.enthalpyTransferType.toElement('enthalpyTransferType'))

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

    def toElement(self, tag: str):
        return E(tag,
                 self.particleType.toElement('particleType'),
                 self.inert.toElement('inert'),
                 self.droplet.toElement('droplet'),
                 self.numericalConditions.toElement('numericalConditions'),
                 self.kinematicModel.toElement('kinematicModel'),
                 self.turbulentDispersion.toElement('turbulentDispersion'),
                 self.heatTransfer.toElement('heatTransfer'),
                 self.evaporation.toElement('evaporation'))



@dataclass
class PointInjection:
    numberOfParticlesPerPoint: PFloat   = field(default_factory=lambda: PFloat('100'))
    injectionTime: PFloat               = field(default_factory=lambda: PFloat('0'))
    particleVelocity: Vector            = field(default_factory=Vector.xUnit)
    positions: list[Vector]             = field(default_factory=list)

    @staticmethod
    def fromElement(e):
        positions = []
        for p in e.findall('positions/position', namespaces=nsmap):
            positions.append(Vector.fromElement(p))

        return PointInjection(
            numberOfParticlesPerPoint=PFloat.fromElement(e.find('numberOfParticlesPerPoint', namespaces=nsmap)),
            injectionTime=PFloat.fromElement(e.find('injectionTime', namespaces=nsmap)),
            particleVelocity=Vector.fromElement(e.find('particleVelocity', namespaces=nsmap)),
            positions=positions
        )

    def toElement(self, tag: str):
        positionsElement = E('positions')
        positionsElement.extend([p.toElement('position') for p in self.positions])
        return E(tag,
            self.numberOfParticlesPerPoint.toElement('numberOfParticlesPerPoint'),
            self.injectionTime.toElement('injectionTime'),
            self.particleVelocity.toElement('particleVelocity'),
            positionsElement)

@dataclass
class ParticleCountParameters:
    parcelPerSecond: PFloat             = field(default_factory=lambda: PFloat('100'))
    numberOfParticlesPerParcel: PFloat  = field(default_factory=lambda: PFloat('100'))

    @staticmethod
    def fromElement(e):
        return ParticleCountParameters(
            parcelPerSecond=PFloat.fromElement(e.find('parcelPerSecond', namespaces=nsmap)),
            numberOfParticlesPerParcel=PFloat.fromElement(
                e.find('numberOfParticlesPerParcel',namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.parcelPerSecond.toElement('parcelPerSecond'),
                 self.numberOfParticlesPerParcel.toElement('numberOfParticlesPerParcel'))

@dataclass
class ParticleVolumeParameters:
    parcelPerSecond: PFloat         = field(default_factory=lambda: PFloat('100'))
    totalMass: PFloat               = field(default_factory=lambda: PFloat('100'))
    volumeFlowRate: Function1Scalar = field(default_factory=lambda: Function1Scalar(constant=PFloat('100')))
    massFlowRate: PFloat            = field(default_factory=lambda: PFloat('100'))

    @staticmethod
    def fromElement(e):
        return ParticleVolumeParameters(
            parcelPerSecond=PFloat.fromElement(e.find('parcelPerSecond', namespaces=nsmap)),
            totalMass=PFloat.fromElement(e.find('totalMass',namespaces=nsmap)),
            volumeFlowRate=Function1Scalar.fromElement(e.find('volumeFlowRate',namespaces=nsmap)),
            massFlowRate=PFloat.fromElement(e.find('massFlowRate',namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.parcelPerSecond.toElement('parcelPerSecond'),
                 self.totalMass.toElement('totalMass'),
                 self.volumeFlowRate.toElement('volumeFlowRate'),
                 self.massFlowRate.toElement('massFlowRate'))

@dataclass
class FlowRate:
    specification: DPMFlowRateSpec              = DPMFlowRateSpec.PARTICLE_COUNT
    particleCount: ParticleCountParameters      = field(default_factory=ParticleCountParameters)
    particleVolume: ParticleVolumeParameters    = field(default_factory=ParticleVolumeParameters)
    startTime: PFloat                           = field(default_factory=lambda: PFloat('0'))
    stopTime: PFloat                            = field(default_factory=lambda: PFloat('1'))

    @staticmethod
    def fromElement(e):
        return FlowRate(
            specification=DPMFlowRateSpec(e.find('specification', namespaces=nsmap).text),
            particleCount=ParticleCountParameters.fromElement(e.find('particleCount', namespaces=nsmap)),
            particleVolume=ParticleVolumeParameters.fromElement(e.find('particleVolume', namespaces=nsmap)),
            startTime=PFloat.fromElement(e.find('startTime', namespaces=nsmap)),
            stopTime=PFloat.fromElement(e.find('stopTime', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.specification.toElement('specification'),
                 self.particleCount.toElement('particleCount'),
                 self.particleVolume.toElement('particleVolume'),
                 self.startTime.toElement('startTime'),
                 self.stopTime.toElement('stopTime'))

@dataclass
class ConeInjection:
    injectorType: DPMConeInjectorType   = DPMConeInjectorType.DISC
    position: Function1Vector           = field(default_factory=lambda: Function1Vector(constant=Vector.xUnit()))
    axis: Function1Vector               = field(default_factory=lambda: Function1Vector(constant=Vector.zUnit()))
    outerConeAngle: Function1Scalar     = field(default_factory=lambda: Function1Scalar(constant=PFloat('30')))
    innerConeAngle: Function1Scalar     = field(default_factory=lambda: Function1Scalar(constant=PFloat('0')))
    outerRadius: PFloat                 = field(default_factory=lambda: PFloat('1'))
    innerRadius: PFloat                 = field(default_factory=lambda: PFloat('0'))
    swirlVelocity: Function1Scalar      = field(default_factory=lambda: Function1Scalar(constant=PFloat('0')))
    particleSpeed: DPMParticleSpeed     = DPMParticleSpeed.FROM_INJECTION_SPEED
    injectionSpeed: PFloat              = field(default_factory=lambda: PFloat('1'))
    injectorPressure: Function1Scalar   = field(default_factory=lambda: Function1Scalar(constant=PFloat('0')))
    dischargeCoeff: Function1Scalar     = field(default_factory=lambda: Function1Scalar(constant=PFloat('0')))

    @staticmethod
    def fromElement(e):
        return ConeInjection(
            injectorType=DPMConeInjectorType(e.find('injectorType', namespaces=nsmap).text),
            position=Function1Vector.fromElement(e.find('position', namespaces=nsmap)),
            axis=Function1Vector.fromElement(e.find('axis', namespaces=nsmap)),
            outerConeAngle=Function1Scalar.fromElement(e.find('outerConeAngle', namespaces=nsmap)),
            innerConeAngle=Function1Scalar.fromElement(e.find('innerConeAngle', namespaces=nsmap)),
            outerRadius=PFloat.fromElement(e.find('outerRadius', namespaces=nsmap)),
            innerRadius=PFloat.fromElement(e.find('innerRadius', namespaces=nsmap)),
            swirlVelocity=Function1Scalar.fromElement(e.find('swirlVelocity', namespaces=nsmap)),
            particleSpeed=DPMParticleSpeed(e.find('particleSpeed', namespaces=nsmap).text),
            injectionSpeed=PFloat.fromElement(e.find('injectionSpeed', namespaces=nsmap)),
            injectorPressure=Function1Scalar.fromElement(e.find('injectorPressure', namespaces=nsmap)),
            dischargeCoeff=Function1Scalar.fromElement(e.find('dischargeCoeff', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.injectorType.toElement('injectorType'),
                 self.position.toElement('position'),
                 self.axis.toElement('axis'),
                 self.outerConeAngle.toElement('outerConeAngle'),
                 self.innerConeAngle.toElement('innerConeAngle'),
                 self.outerRadius.toElement('outerRadius'),
                 self.innerRadius.toElement('innerRadius'),
                 self.swirlVelocity.toElement('swirlVelocity'),
                 self.particleSpeed.toElement('particleSpeed'),
                 self.injectionSpeed.toElement('injectionSpeed'),
                 self.injectorPressure.toElement('injectorPressure'),
                 self.dischargeCoeff.toElement('dischargeCoeff'))

@dataclass
class ParticleVelocity:
    type: DPMParticleVelocityType   = DPMParticleVelocityType.CONSTANT
    value: Vector                   = field(default_factory=Vector.xUnit)

    @staticmethod
    def fromElement(e):
        return ParticleVelocity(type=DPMParticleVelocityType(e.find('type', namespaces=nsmap).text),
                                value=Vector.fromElement(e.find('value', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.type.toElement('type'),
                 self.value.toElement('value'))

@dataclass
class SurfaceInjection:
    particleVelocity: ParticleVelocity  = field(default_factory=ParticleVelocity)
    bcid: str                           = '0'

    @staticmethod
    def fromElement(e):
        return SurfaceInjection(
            particleVelocity=ParticleVelocity.fromElement(e.find('particleVelocity', namespaces=nsmap)),
            bcid=e.find('surface', namespaces=nsmap).text)

    def toElement(self, tag: str):
        return E(tag,
                 self.particleVelocity.toElement('particleVelocity'),
                 E('surface', self.bcid))


@dataclass
class InjectorProperties:
    pointInjection: PointInjection      = field(default_factory=PointInjection)
    flowRate: FlowRate                  = field(default_factory=FlowRate)
    surfaceInjection: SurfaceInjection  = field(default_factory=SurfaceInjection)
    coneInjection: ConeInjection        = field(default_factory=ConeInjection)

    @staticmethod
    def fromElement(e):
        return InjectorProperties(pointInjection=PointInjection.fromElement(e.find('pointInjection', namespaces=nsmap)),
                        flowRate=FlowRate.fromElement(e.find('flowRate', namespaces=nsmap)),
                        surfaceInjection=SurfaceInjection.fromElement(e.find('surfaceInjection', namespaces=nsmap)),
                        coneInjection=ConeInjection.fromElement(e.find('coneInjection', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
            self.pointInjection.toElement('pointInjection'),
            self.flowRate.toElement('flowRate'),
            self.coneInjection.toElement('coneInjection'),
            self.surfaceInjection.toElement('surfaceInjection'))

@dataclass
class DiameterDistribution:
    type: DPMDiameterDistribution   = DPMDiameterDistribution.UNIFORM
    diameter: PFloat                = field(default_factory=lambda: PFloat('0.0001'))
    minDiameter: PFloat             = field(default_factory=lambda: PFloat('0.0001'))
    maxDiameter: PFloat             = field(default_factory=lambda: PFloat('0.0001'))
    meanDiameter: PFloat            = field(default_factory=lambda: PFloat('0.0001'))
    spreadParameter: PFloat         = field(default_factory=lambda: PFloat('0.0001'))
    stdDeviation: PFloat            = field(default_factory=lambda: PFloat('0.0001'))

    @staticmethod
    def fromElement(e):
        return DiameterDistribution(
            type=DPMDiameterDistribution(e.find('type', namespaces=nsmap).text),
            diameter=PFloat.fromElement(e.find('diameter', namespaces=nsmap)),
            minDiameter=PFloat.fromElement(e.find('minDiameter', namespaces=nsmap)),
            maxDiameter=PFloat.fromElement(e.find('maxDiameter', namespaces=nsmap)),
            meanDiameter=PFloat.fromElement(e.find('meanDiameter', namespaces=nsmap)),
            spreadParameter=PFloat.fromElement(e.find('spreadParameter', namespaces=nsmap)),
            stdDeviation=PFloat.fromElement(e.find('stdDeviation', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
            E('type', self.type.value),
            self.diameter.toElement('diameter'),
            self.minDiameter.toElement('minDiameter'),
            self.maxDiameter.toElement('maxDiameter'),
            self.meanDiameter.toElement('meanDiameter'),
            self.spreadParameter.toElement('spreadParameter'),
            self.stdDeviation.toElement('stdDeviation'))

@dataclass
class Injection:
    name: str                                   = ''
    type: DPMInjectionType                      = DPMInjectionType.CONE
    injector: InjectorProperties                = field(default_factory=InjectorProperties)
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
            type=DPMInjectionType(e.find('type', namespaces=nsmap).text),
            injector=InjectorProperties.fromElement(e.find('injectorProperties', namespaces=nsmap)),
            diameterDistribution=DiameterDistribution.fromElement(e.find('diameterDistribution', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 E('name', self.name),
                 self.type.toElement('type'),
                 self.injector.toElement('injectorProperties'),
                 self.diameterDistribution.toElement('diameterDistribution'))


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
    def updateDPMModel(db, properties: DPMModelProperties, injections: list[Injection]):
        dpmModels = db.getElement(DPM_MODELS_XPATH)

        if injections:
            injectionsElement = E('injections')
            injectionsElement.extend([i.toElement('injection') for i in injections])
        else:  # Not modified
            injectionsElement = dpmModels.find('injections', namespaces=nsmap)

        dpmModels.clear()
        dpmModels.append(properties.toElement('properties'))
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
