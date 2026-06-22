#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from xml.etree.ElementTree import Element

from libbaram.pfloat import PFloat

from baramFlow.base.base import NumberList
from baramFlow.coredb.libdb import nsmap, E
from .constants import SpecificHeatSpecification


@dataclass
class JanafSpecificHeat:
    lowTemperature: PFloat          = field(default_factory=lambda: PFloat('200'))
    commonTemperature: PFloat       = field(default_factory=lambda: PFloat('1000'))
    highTemperature: PFloat         = field(default_factory=lambda: PFloat('6000'))
    lowCoefficients: NumberList     = field(default_factory=lambda: NumberList.zeros(7))
    highCoefficients: NumberList    = field(default_factory=lambda: NumberList.zeros(7))

    @staticmethod
    def fromElement(e: Element):
        return JanafSpecificHeat(
            lowTemperature=PFloat.fromElement(e.find('lowTemperature', namespaces=nsmap)),
            commonTemperature=PFloat.fromElement(e.find('commonTemperature', namespaces=nsmap)),
            highTemperature=PFloat.fromElement(e.find('highTemperature', namespaces=nsmap)),
            lowCoefficients=NumberList.fromElement(e.find('lowCoefficients', namespaces=nsmap)),
            highCoefficients=NumberList.fromElement(e.find('highCoefficients', namespaces=nsmap)))

    def toElement(self):
        return E('janaf',
                 self.lowTemperature.toElement('lowTemperature'),
                 self.commonTemperature.toElement('commonTemperature'),
                 self.highTemperature.toElement('highTemperature'),
                 self.lowCoefficients.toElement('lowCoefficients'),
                 self.highCoefficients.toElement('highCoefficients'))


@dataclass(kw_only=True)
class SpecificHeat:
    specification: SpecificHeatSpecification    = SpecificHeatSpecification.CONSTANT
    constant: PFloat
    polynomial: NumberList                      = field(default_factory=NumberList.zeros)
    janaf: JanafSpecificHeat                    = field(default_factory=JanafSpecificHeat)

    @staticmethod
    def fromElement(e: Element):
        return SpecificHeat(specification=SpecificHeatSpecification(e.find('specification', namespaces=nsmap).text),
                            constant=PFloat.fromElement(e.find('constant', namespaces=nsmap)),
                            polynomial=NumberList.fromElement(e.find('polynomial', namespaces=nsmap)),
                            janaf=JanafSpecificHeat.fromElement(e.find('janaf', namespaces=nsmap)))

    def toElement(self):
        return E('specificHeat',
                 E('specification', self.specification),
                 self.constant.toElement('constant'),
                 self.polynomial.toElement('polynomial'),
                 self.janaf.toElement())