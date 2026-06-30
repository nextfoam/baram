#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from enum import Enum
from xml.etree.ElementTree import Element

from lxml import etree

from baramFlow.base.base import TemporalScalarList, NumberList
from baramFlow.coredb.region_db import CELL_ZONE_NAME_FOR_REGION
from libbaram.pfloat import PFloat
from resources import resource

from baramFlow.coredb.libdb import nsmap, xmlToBool, E

CELL_ZONE_ELEMENT_PATH = 'configurations/cell_zone.xml'


class SpecificationMethod(Enum):
    VALUE_PER_UNIT_VOLUME = 'valuePerUnitVolume'
    VALUE_FOR_ENTIRE_CELL_ZONE = 'valueForEntireCellZone'


class TemporalProfileType(Enum):
    CONSTANT = 'constant'
    PIECEWISE_LINEAR = 'piecewiseLinear'
    POLYNOMIAL = 'polynomial'


@dataclass
class VariableSourceTerm:
    unit: SpecificationMethod           = SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE
    specification: TemporalProfileType  = TemporalProfileType.CONSTANT
    constant: PFloat                    = field(default_factory=lambda: PFloat('0'))
    piecewiseLinear: TemporalScalarList = field(default_factory=TemporalScalarList.default)
    polynomial: NumberList              = field(default_factory=NumberList.zeros)
    disabled: bool                      = True

    @staticmethod
    def fromElement(e: Element):
        return VariableSourceTerm(
            unit=SpecificationMethod(e.find('unit', namespaces=nsmap).text),
            specification=TemporalProfileType(e.find('specification', namespaces=nsmap).text),
            constant=PFloat(e.find('constant', namespaces=nsmap).text),
            piecewiseLinear=TemporalScalarList.fromElement(e.find('piecewiseLinear', namespaces=nsmap)),
            polynomial=NumberList.fromElement(e.find('polynomial', namespaces=nsmap)),
            disabled=xmlToBool(e.get('disabled')))

    def toElement(self, tag: str):
        return E(tag,
                 E('unit', self.unit),
                 E('specification', self.specification),
                 self.constant.toElement('constant'),
                 self.piecewiseLinear.toElement('piecewiseLinear'),
                 self.polynomial.toElement('polynomial'),
                 disabled=self.disabled)


@dataclass
class ConstantSourceTerm:
    unit: SpecificationMethod   = SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE
    constant: PFloat            = field(default_factory=lambda: PFloat('0'))
    disabled: bool              = True

    @staticmethod
    def fromElement(e: Element):
        return ConstantSourceTerm(
            unit=SpecificationMethod(e.find('unit', namespaces=nsmap).text),
            constant=PFloat(e.find('constant', namespaces=nsmap).text),
            disabled=xmlToBool(e.get('disabled')))

    def toElement(self, tag: str):
        return E(tag,
                 E('unit', self.unit),
                 self.constant.toElement('constant'),
                 disabled=self.disabled)


@dataclass
class SourceTerms:
    mass: VariableSourceTerm                            = field(default_factory=VariableSourceTerm)
    materials: dict[str, VariableSourceTerm]            = field(default_factory=dict)
    energy: VariableSourceTerm                          = field(default_factory=VariableSourceTerm)
    turbulentKineticEnergy: ConstantSourceTerm          = field(default_factory=ConstantSourceTerm)
    turbulentDissipationRate: ConstantSourceTerm        = field(default_factory=ConstantSourceTerm)
    specificDissipationRate: ConstantSourceTerm         = field(default_factory=ConstantSourceTerm)
    modifiedTurbulentViscosity: ConstantSourceTerm      = field(default_factory=ConstantSourceTerm)
    userDefinedScalars: dict[str, VariableSourceTerm]   = field(default_factory=dict)

    @staticmethod
    def fromElement(e: Element):
        return SourceTerms(
            mass=VariableSourceTerm.fromElement(e.find('mass', namespaces=nsmap)),
            materials={m.find('material', namespaces=nsmap).text: VariableSourceTerm.fromElement(m)
                       for m in e.findall('materials/materialSource', namespaces=nsmap)},
            energy=VariableSourceTerm.fromElement(e.find('energy', namespaces=nsmap)),
            turbulentKineticEnergy=ConstantSourceTerm.fromElement(
                e.find('turbulentKineticEnergy', namespaces=nsmap)),
            turbulentDissipationRate=ConstantSourceTerm.fromElement(
                e.find('turbulentDissipationRate', namespaces=nsmap)),
            specificDissipationRate=ConstantSourceTerm.fromElement(
                e.find('specificDissipationRate', namespaces=nsmap)),
            modifiedTurbulentViscosity=ConstantSourceTerm.fromElement(
                e.find('modifiedTurbulentViscosity', namespaces=nsmap)),
            userDefinedScalars={m.find('scalarID', namespaces=nsmap).text: VariableSourceTerm.fromElement(m)
                                for m in e.findall('userDefinedScalars/scalarSource', namespaces=nsmap)})

    def toElement(self):
        materials = E('materials')
        for mid, data in self.materials.items():
            e = data.toElement('materialSource')
            e.insert(0, E('material', mid))
            materials.append(e)

        scalars = E('userDefinedScalars')
        for sid, data in self.userDefinedScalars.items():
            e = data.toElement('scalarSource')
            e.insert(0, E('scalarID', sid))
            scalars.append(e)

        return E('sourceTerms',
                 self.mass.toElement('mass'),
                 materials,
                 self.energy.toElement('energy'),
                 self.turbulentKineticEnergy.toElement('turbulentKineticEnergy'),
                 self.turbulentDissipationRate.toElement('turbulentDissipationRate'),
                 self.specificDissipationRate.toElement('specificDissipationRate'),
                 self.modifiedTurbulentViscosity.toElement('modifiedTurbulentViscosity'),
                 scalars)


@dataclass(kw_only=True)
class CellZoneData:
    czid: str   = ''
    name: str
    rname: str  = ''

    sourceTerms: SourceTerms    = field(default_factory=SourceTerms)

    def isRegion(self):
        return self.name == CELL_ZONE_NAME_FOR_REGION

    def toElement(self):
        with open(resource.file(CELL_ZONE_ELEMENT_PATH), 'rb') as file:
            xml = file.read()

        element = etree.fromstring(xml)
        element.set('czid', self.czid)
        element.find('name', namespaces=nsmap).text = self.name

        return element

    @staticmethod
    def fromElement(e: Element):
        return CellZoneData(
            czid=e.get('czid'),
            name=e.find('name', namespaces=nsmap).text,
            sourceTerms=SourceTerms.fromElement(e.find('sourceTerms', namespaces=nsmap)))
