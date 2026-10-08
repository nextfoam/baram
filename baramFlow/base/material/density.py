#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from xml.etree.ElementTree import Element

from libbaram.pfloat import PFloat

from baramFlow.base.base import NumberList
from baramFlow.coredb.libdb import nsmap, E
from .constants import DensitySpecification, Phase, MaterialType


@dataclass
class Boussinesq:
    rho0: PFloat    = field(default_factory=lambda: PFloat('1'))
    t0: PFloat      = field(default_factory=lambda: PFloat('300'))
    beta: PFloat    = field(default_factory=lambda: PFloat('3e-03'))

    @staticmethod
    def fromElement(e: Element):
        if e is None:
            return None

        return Boussinesq(rho0=PFloat.fromElement(e.find('rho0', namespaces=nsmap)),
                          t0=PFloat.fromElement(e.find('T0', namespaces=nsmap)),
                          beta=PFloat.fromElement(e.find('beta', namespaces=nsmap)))

    def toElement(self):
        return E('boussinesq',
                 self.rho0.toElement('rho0'),
                 self.t0.toElement('T0'),
                 self.beta.toElement('beta'))


@dataclass
class PerfectFluid:
    rho0: PFloat    = field(default_factory=lambda: PFloat('997'))
    t: PFloat       = field(default_factory=lambda: PFloat('288'))
    beta: PFloat    = field(default_factory=lambda: PFloat('4.609e-10'))

    @staticmethod
    def fromElement(e: Element):
        if e is None:
            return None

        return PerfectFluid(rho0=PFloat.fromElement(e.find('rho0', namespaces=nsmap)),
                            t=PFloat.fromElement(e.find('T', namespaces=nsmap)),
                            beta=PFloat.fromElement(e.find('beta', namespaces=nsmap)))

    def toElement(self):
        return E('perfectFluid',
                 self.rho0.toElement('rho0'),
                 self.t.toElement('T'),
                 self.beta.toElement('beta'))


@dataclass(kw_only=True)
class Density:
    specification: DensitySpecification
    constant: PFloat
    polynomial: NumberList
    boussinesq: Boussinesq | None           = None
    perfectFluid: PerfectFluid | None       = None

    @staticmethod
    def default(constant: str, phase: Phase, type: MaterialType):
        default = Density(specification=DensitySpecification.CONSTANT,
                          constant=PFloat(constant),
                          polynomial=NumberList.zeros())

        if type != MaterialType.MIXTURE:
            if phase == Phase.GAS:
                default.boussinesq = Boussinesq()
            elif phase == Phase.LIQUID:
                default.perfectFluid = PerfectFluid()

        return default

    @staticmethod
    def fromElement(e: Element):
        return Density(specification=DensitySpecification(e.find('specification', namespaces=nsmap).text),
                       constant=PFloat.fromElement(e.find('constant', namespaces=nsmap)),
                       polynomial=NumberList.fromElement(e.find('polynomial', namespaces=nsmap)),
                       boussinesq= Boussinesq.fromElement(e.find('boussinesq', namespaces=nsmap)),
                       perfectFluid=PerfectFluid.fromElement(e.find('perfectFluid', namespaces=nsmap)))

    def toElement(self):
        elements = [
            E('specification', self.specification),
            self.constant.toElement('constant'),
            self.polynomial.toElement('polynomial')]

        if self.boussinesq is not None:
            elements.append(self.boussinesq.toElement())

        if self.perfectFluid is not None:
            elements.append(self.perfectFluid.toElement())

        return E('density',
                 *[e for e in elements if e is not None])
