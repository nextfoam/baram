#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from xml.etree.ElementTree import Element

from libbaram.pfloat import PFloat

from baramFlow.base.base import NumberList
from baramFlow.coredb.libdb import nsmap, E
from .constants import TransportSpecification, Phase


@dataclass
class Specifications:
    density: str = 'constant'
    specificHeat: str = 'constant'
    transport: str = 'constant'


@dataclass
class PolynomialTransport:
    viscosity: NumberList           = field(default_factory=NumberList.zeros)
    thermalConductivity: NumberList = field(default_factory=NumberList.zeros)

    @staticmethod
    def fromElement(e: Element):
        return PolynomialTransport(
            viscosity=NumberList.fromElement(e.find('viscosity', namespaces=nsmap)),
            thermalConductivity=NumberList.fromElement(e.find('thermalConductivity', namespaces=nsmap)))

    def toElement(self):
        return E('polynomial',
                 self.viscosity.toElement('viscosity'),
                 self.thermalConductivity.toElement('thermalConductivity'))


@dataclass
class Sutherland:
    coefficient: PFloat
    temperature: PFloat

    @staticmethod
    def fromElement(e: Element):
        if e is None:
            return None

        return Sutherland(coefficient=PFloat.fromElement(e.find('coefficient', namespaces=nsmap)),
                          temperature=PFloat.fromElement(e.find('temperature', namespaces=nsmap)))

    def toElement(self):
        return E('sutherland',
                 self.coefficient.toElement('coefficient'),
                 self.temperature.toElement('temperature'))


@dataclass
class CrossViscosity:
    zeroShearViscosity: PFloat      = field(default_factory=lambda: PFloat('1e-01'))
    infiniteShearViscosity: PFloat  = field(default_factory=lambda: PFloat('1.5e-05'))
    naturalTime: PFloat             = field(default_factory=lambda: PFloat('1'))
    powerLawIndex: PFloat           = field(default_factory=lambda: PFloat('0.5'))

    @staticmethod
    def fromElement(e: Element):
        if e is None:
            return None

        return CrossViscosity(
            zeroShearViscosity=PFloat.fromElement(e.find('zeroShearViscosity', namespaces=nsmap)),
            infiniteShearViscosity=PFloat.fromElement(e.find('infiniteShearViscosity', namespaces=nsmap)),
            naturalTime=PFloat.fromElement(e.find('naturalTime', namespaces=nsmap)),
            powerLawIndex=PFloat.fromElement(e.find('powerLawIndex', namespaces=nsmap)))

    def toElement(self):
        return E('cross',
                 self.zeroShearViscosity.toElement('zeroShearViscosity'),
                 self.infiniteShearViscosity.toElement('infiniteShearViscosity'),
                 self.naturalTime.toElement('naturalTime'),
                 self.powerLawIndex.toElement('powerLawIndex'))


@dataclass
class HerschelBulkleyViscosity:
    zeroShearViscosity: PFloat      = field(default_factory=lambda: PFloat('1.5e-04'))
    yieldStressThreshold: PFloat    = field(default_factory=lambda: PFloat('1.75e-05'))
    consistencyIndex: PFloat        = field(default_factory=lambda: PFloat('8.9721e-3'))
    powerLawIndex: PFloat           = field(default_factory=lambda: PFloat('0.8601'))

    @staticmethod
    def fromElement(e: Element):
        if e is None:
            return None

        return HerschelBulkleyViscosity(
            zeroShearViscosity=PFloat.fromElement(e.find('zeroShearViscosity', namespaces=nsmap)),
            yieldStressThreshold=PFloat.fromElement(e.find('yieldStressThreshold', namespaces=nsmap)),
            consistencyIndex=PFloat.fromElement(e.find('consistencyIndex', namespaces=nsmap)),
            powerLawIndex=PFloat.fromElement(e.find('powerLawIndex', namespaces=nsmap)))

    def toElement(self):
        return E('herschelBulkley',
                 self.zeroShearViscosity.toElement('zeroShearViscosity'),
                 self.yieldStressThreshold.toElement('yieldStressThreshold'),
                 self.consistencyIndex.toElement('consistencyIndex'),
                 self.powerLawIndex.toElement('powerLawIndex'))


@dataclass
class CarreauViscosity:
    zeroShearViscosity: PFloat      = field(default_factory=lambda: PFloat('1e-01'))
    infiniteShearViscosity: PFloat  = field(default_factory=lambda: PFloat('0'))
    relaxationTime: PFloat          = field(default_factory=lambda: PFloat('0.0084033613'))
    powerLawIndex: PFloat           = field(default_factory=lambda: PFloat('0.353'))
    linearityDeviation: PFloat      = field(default_factory=lambda: PFloat('1.433'))

    @staticmethod
    def fromElement(e: Element):
        if e is None:
            return None

        return CarreauViscosity(
            zeroShearViscosity=PFloat.fromElement(e.find('zeroShearViscosity', namespaces=nsmap)),
            infiniteShearViscosity=PFloat.fromElement(e.find('infiniteShearViscosity', namespaces=nsmap)),
            relaxationTime=PFloat.fromElement(e.find('relaxationTime', namespaces=nsmap)),
            powerLawIndex=PFloat.fromElement(e.find('powerLawIndex', namespaces=nsmap)),
            linearityDeviation=PFloat.fromElement(e.find('linearityDeviation', namespaces=nsmap)))

    def toElement(self):
        return E('carreau',
                 self.zeroShearViscosity.toElement('zeroShearViscosity'),
                 self.infiniteShearViscosity.toElement('infiniteShearViscosity'),
                 self.relaxationTime.toElement('relaxationTime'),
                 self.powerLawIndex.toElement('powerLawIndex'),
                 self.linearityDeviation.toElement('linearityDeviation'))


@dataclass
class NonNewtonianPowerLawViscosity:
    maximumViscosity: PFloat    = field(default_factory=lambda: PFloat('1e-03'))
    minimumViscosity: PFloat    = field(default_factory=lambda: PFloat('1e-06'))
    consistencyIndex: PFloat    = field(default_factory=lambda: PFloat('8.42'))
    powerLawIndex: PFloat       = field(default_factory=lambda: PFloat('0.61'))

    @staticmethod
    def fromElement(e: Element):
        if e is None:
            return None

        return NonNewtonianPowerLawViscosity(
            maximumViscosity=PFloat.fromElement(e.find('maximumViscosity', namespaces=nsmap)),
            minimumViscosity=PFloat.fromElement(e.find('minimumViscosity', namespaces=nsmap)),
            consistencyIndex=PFloat.fromElement(e.find('consistencyIndex', namespaces=nsmap)),
            powerLawIndex=PFloat.fromElement(e.find('powerLawIndex', namespaces=nsmap)))

    def toElement(self):
        return E('nonNewtonianPowerLaw',
                 self.maximumViscosity.toElement('maximumViscosity'),
                 self.minimumViscosity.toElement('minimumViscosity'),
                 self.consistencyIndex.toElement('consistencyIndex'),
                 self.powerLawIndex.toElement('powerLawIndex'))


@dataclass(kw_only=True)
class Transport:
    specification: TransportSpecification                       = TransportSpecification.CONSTANT
    viscosity: PFloat
    thermalConductivity: PFloat
    polynomial: PolynomialTransport
    sutherland: Sutherland | None                               = None
    crossPowerLaw: CrossViscosity | None                        = None
    herschelBulkley: HerschelBulkleyViscosity | None            = None
    birdCarreau: CarreauViscosity | None                        = None
    nonNewtonianPowerLaw: NonNewtonianPowerLawViscosity | None  = None

    @staticmethod
    def fromBase(base: dict, phase):
        default = Transport(viscosity=PFloat(base['viscosity']),
                            thermalConductivity=PFloat(base['thermalConductivity']),
                            polynomial=PolynomialTransport())

        if phase == Phase.GAS:
            default.sutherland = Sutherland(coefficient=PFloat(base['sutherlandCoefficient']),
                                            temperature=PFloat(base['sutherlandTemperature']))
        elif phase == Phase.LIQUID:
            default.crossPowerLaw = CrossViscosity()
            default.herschelBulkley = HerschelBulkleyViscosity()
            default.birdCarreau = CarreauViscosity()
            default.nonNewtonianPowerLaw = NonNewtonianPowerLawViscosity()

        return default

    @staticmethod
    def fromElement(e: Element):
        return Transport(
            specification=TransportSpecification(e.find('specification', namespaces=nsmap).text),
            viscosity=PFloat.fromElement(e.find('viscosity', namespaces=nsmap)),
            thermalConductivity=PFloat.fromElement(e.find('thermalConductivity', namespaces=nsmap)),
            polynomial=PolynomialTransport.fromElement(e.find('polynomial', namespaces=nsmap)),
            sutherland=Sutherland.fromElement(e.find('sutherland', namespaces=nsmap)),
            crossPowerLaw=CrossViscosity.fromElement(e.find('cross', namespaces=nsmap)),
            herschelBulkley=HerschelBulkleyViscosity.fromElement(e.find('herschelBulkley', namespaces=nsmap)),
            birdCarreau=CarreauViscosity.fromElement(e.find('carreau', namespaces=nsmap)),
            nonNewtonianPowerLaw=NonNewtonianPowerLawViscosity.fromElement(
                e.find('nonNewtonianPowerLaw', namespaces=nsmap)))

    def toElement(self):
        elements = [
            E('specification', self.specification),
            self.viscosity.toElement('viscosity'),
            self.thermalConductivity.toElement('thermalConductivity')]

        if self.polynomial is not None:
            elements.append(self.polynomial.toElement())

        if self.sutherland is not None:
            elements.append(self.sutherland.toElement())

        if self.crossPowerLaw is not None:
            elements.append(self.crossPowerLaw.toElement())

        if self.herschelBulkley is not None:
            elements.append(self.herschelBulkley.toElement())

        if self.birdCarreau is not None:
            elements.append(self.birdCarreau.toElement())

        if self.nonNewtonianPowerLaw is not None:
            elements.append(self.nonNewtonianPowerLaw.toElement())

        return E('transport',
                 *[e for e in elements if e is not None])

