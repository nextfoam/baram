#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum

from xml.sax.saxutils import escape

import baramFlow.coredb.libdb as xml
from .materials_base import MaterialsBase


class Phase(Enum):
    GAS = 'gas'
    LIQUID = 'liquid'
    SOLID = 'solid'


class Specification(Enum):
    CONSTANT = 'constant'
    PERFECT_GAS = 'perfectGas'
    SUTHERLAND = 'sutherland'
    POLYNOMIAL = 'polynomial'


class DensitySpecification(Enum):
    CONSTANT = 'constant'
    PERFECT_GAS = 'perfectGas'
    POLYNOMIAL = 'polynomial'
    INCOMPRESSIBLE_PERFECT_GAS = 'incompressiblePerfectGas'
    REAL_GAS_PENG_ROBINSON = 'PengRobinsonGas'


class ViscositySpecification(Enum):
    CONSTANT = 'constant'
    PERFECT_GAS = 'perfectGas'
    SUTHERLAND = 'sutherland'
    POLYNOMIAL = 'polynomial'
    CROSS_POWER_LAW = 'cross'
    HERSCHEL_BULKLEY = 'herschelBulkley'
    BIRD_CARREAU = 'carreau'
    POWER_LAW = 'nonNewtonianPowerLaw'


class MaterialType(Enum):
    NONMIXTURE = 'nonmixture'
    MIXTURE = 'mixture'
    SPECIE = 'specie'


@dataclass
class Specifications:
    density: str = 'constant'
    specificHeat: str = 'constant'
    thermalConductivity: str = 'constant'
    viscosity: str = 'constant'


@dataclass
class CrossViscosity:
    zeroShearViscosity: str = '1e-01'
    infiniteShearViscosity: str = '1.5e-05'
    naturalTime: str = '1'
    powerLawIndex: str = '0.5'

    def toXML(self):
        return f'''<cross xmlns="http://www.baramcfd.org/baram">
                    <zeroShearViscosity>{self.zeroShearViscosity}</zeroShearViscosity>
                    <infiniteShearViscosity>{self.infiniteShearViscosity}</infiniteShearViscosity>
                    <naturalTime>{self.naturalTime}</naturalTime>
                    <powerLawIndex>{self.powerLawIndex}</powerLawIndex>
                   </cross>'''


@dataclass
class HerschelBulkleyViscosity:
    zeroShearViscosity: str = '1.5e-04'
    yieldStressThreshold: str = '1.75e-05'
    consistencyIndex: str = '8.9721e-3'
    powerLawIndex: str = '0.8601'

    def toXML(self):
        return f'''<herschelBulkley xmlns="http://www.baramcfd.org/baram">
                    <zeroShearViscosity>{self.zeroShearViscosity}</zeroShearViscosity>
                    <yieldStressThreshold>{self.yieldStressThreshold}</yieldStressThreshold>
                    <consistencyIndex>{self.consistencyIndex}</consistencyIndex>
                    <powerLawIndex>{self.powerLawIndex}</powerLawIndex>
                   </herschelBulkley>'''


@dataclass
class CarreauViscosity:
    zeroShearViscosity: str = '1e-01'
    infiniteShearViscosity: str = '0'
    relaxationTime: str = '0.0084033613'
    powerLawIndex: str = '0.353'
    linearityDeviation: str = '1.433'

    def toXML(self):
        return f'''<carreau xmlns="http://www.baramcfd.org/baram">
                    <zeroShearViscosity>{self.zeroShearViscosity}</zeroShearViscosity>
                    <infiniteShearViscosity>{self.infiniteShearViscosity}</infiniteShearViscosity>
                    <relaxationTime>{self.relaxationTime}</relaxationTime>
                    <powerLawIndex>{self.powerLawIndex}</powerLawIndex>
                    <linearityDeviation>{self.linearityDeviation}</linearityDeviation>
                   </carreau>'''


@dataclass
class NonNewtonianPowerLawViscosity:
    maximumViscosity: str = '1e-03'
    minimumViscosity: str = '1e-06'
    consistencyIndex: str = '8.42'
    powerLawIndex: str = '0.61'

    def toXML(self):
        return f'''<nonNewtonianPowerLaw xmlns="http://www.baramcfd.org/baram">
                    <maximumViscosity>{self.maximumViscosity}</maximumViscosity>
                    <minimumViscosity>{self.minimumViscosity}</minimumViscosity>
                    <consistencyIndex>{self.consistencyIndex}</consistencyIndex>
                    <powerLawIndex>{self.powerLawIndex}</powerLawIndex>
                   </nonNewtonianPowerLaw>'''


@dataclass
class ViscosityProperties:
    crossViscosity: CrossViscosity
    hershelBulkleyViscosity: HerschelBulkleyViscosity
    carreauViscosity: CarreauViscosity
    nonNewtonianPowerLawViscosity: NonNewtonianPowerLawViscosity


@dataclass
class MaterialDefaults:
    specifications: Specifications
    viscosityProperties: ViscosityProperties


_defaultSpecification = Specifications()
_defaultsViscosityProperties = ViscosityProperties(crossViscosity=CrossViscosity(),
                                                   hershelBulkleyViscosity=HerschelBulkleyViscosity(),
                                                   carreauViscosity=CarreauViscosity(),
                                                   nonNewtonianPowerLawViscosity=NonNewtonianPowerLawViscosity())

@dataclass
class TypeProperties:
    type: MaterialType
    mixtureID: str=None  # For specie


def _propertyElement(name,value):
    return '' if value is None else f"<{name}>{value}</{name}>"


def _pengRobinsonXML(values):
    return ("<pengRobinsonParameters>"
            f"  <criticalTemperature>{values['criticalTemperature']}</criticalTemperature>"
            f"  <criticalPressure>{values['criticalPressure']}</criticalPressure>"
            f"  <criticalSpecificVolume>{round(1 / float(values['criticalDensity']), 4)}</criticalSpecificVolume>"
            f"  <acentricFactor>{values['acentricFactor']}</acentricFactor>"
            "</pengRobinsonParameters>")


def _viscosityXML(phase, specification, values, viscosityProperties):
    def sutherland(values_):
        return ("<sutherland>"
                f"  <coefficient>{values_['sutherlandCoefficient']}</coefficient>"
                f"  <temperature>{values_['sutherlandTemperature']}</temperature>"
                "</sutherland>")

    if phase == Phase.SOLID.value:
        return ''

    return ("<viscosity>"
            f"  <specification>{specification}</specification>"
            f"  <constant>{values['viscosity']}</constant>"
            "   <polynomial>0</polynomial>"
            f"  {sutherland(values) if phase == 'gas' else ''}"
            f"  {viscosityProperties.crossViscosity.toXML() if phase == 'liquid' else ''}"
            f"  {viscosityProperties.hershelBulkleyViscosity.toXML() if phase == 'liquid' else ''}"
            f"  {viscosityProperties.carreauViscosity.toXML() if phase == 'liquid' else ''}"
            f"  {viscosityProperties.nonNewtonianPowerLawViscosity.toXML() if phase == 'liquid' else ''}"
            "</viscosity>")


def _typeXML(type, typeProperties):
    if type == MaterialType.MIXTURE:
        return '<mixture><massDiffusivity>1e-10</massDiffusivity><primarySpecie>0</primarySpecie></mixture>'

    if type == MaterialType.SPECIE:
        return f'<specie><mixture>{typeProperties.mixtureID}</mixture></specie>'

    return None


def _materialXML(mid: str, name: str, base: dict, defaults: MaterialDefaults, typeProperties: TypeProperties):
    type_ = typeProperties.type
    specifications = defaults.specifications

    phase = base['phase']
    chemicalFormula = (f"<chemicalFormula>{escape(base['chemicalFormula'])}</chemicalFormula>"
                       if base['chemicalFormula'] else '')

    typeXML = _typeXML(type_, typeProperties)

    xml = f'''
        <material mid="{mid}" xmlns="http://www.baramcfd.org/baram">
            <name>{name}</name>
            <type>{type_.value}</type>
            {chemicalFormula}
            <phase>{phase}</phase>
            {_propertyElement('molecularWeight', base['molecularWeight'])}
            {_propertyElement('absorptionCoefficient', base['absorptionCoefficient'])}
            {_propertyElement('saturationPressure', base['saturationPressure'])}
            {_propertyElement('emissivity', base['emissivity'])}
            <density>
                <specification>{specifications.density}</specification>
                <constant>{base['density']}</constant>
                <polynomial>0</polynomial>
                {_pengRobinsonXML(base) if type_ != MaterialType.MIXTURE and phase == 'gas' else ''}
            </density>
            <specificHeat>
                <specification>{specifications.specificHeat}</specification>
                <constant>{base['specificHeat']}</constant>
                <polynomial>0</polynomial>
            </specificHeat>
            {_viscosityXML(phase, specifications.viscosity, base, defaults.viscosityProperties)}
            <thermalConductivity>
                <specification>{specifications.thermalConductivity}</specification>
                <constant>{base['thermalConductivity']}</constant>
                <polynomial>0</polynomial>
            </thermalConductivity>
            {'' if typeXML is None else typeXML}
        </material>
    '''

    return xml


class MaterialSchema:
    @classmethod
    def newNonMixture(cls, mid: str, name: str, baseName: str):
        return xml.createElement(
            _materialXML(mid, name, MaterialsBase.getMaterial(baseName),
                         MaterialDefaults(_defaultSpecification, _defaultsViscosityProperties),
                         TypeProperties(MaterialType.NONMIXTURE)))

    @classmethod
    def newMixture(cls, mid: str, name: str, specieBaseName: str):
        base = MaterialsBase.getMixture()
        base['phase'] = MaterialsBase.getMaterial(specieBaseName)['phase']

        return xml.createElement(
            _materialXML(mid, name, base,
                         MaterialDefaults(_defaultSpecification, _defaultsViscosityProperties),
                         TypeProperties(MaterialType.MIXTURE)))

    @classmethod
    def newSpecie(cls, mid: str, name: str, baseName: str, defaults: MaterialDefaults, mixtureID: str):
        return xml.createElement(
            _materialXML(mid, name, MaterialsBase.getMaterial(baseName), defaults,
                         TypeProperties(MaterialType.SPECIE, mixtureID)))

    @classmethod
    def defaultsToInherit(cls, mixture):
        viscosityProperties = None
        if xml.getText(mixture, 'phase') == 'liquid':
            viscosity = xml.getElement(mixture, 'viscosity')
            cross = xml.getElement(viscosity, 'cross')
            herSchelBulkley = xml.getElement(viscosity, 'herschelBulkley')
            carreau = xml.getElement(viscosity, 'carreau')
            nonNewtonianPowerLaw = xml.getElement(viscosity, 'nonNewtonianPowerLaw')

            viscosityProperties = ViscosityProperties(
                crossViscosity=CrossViscosity(
                    zeroShearViscosity=xml.getText(cross, 'zeroShearViscosity'),
                    infiniteShearViscosity=xml.getText(cross, 'infiniteShearViscosity'),
                    naturalTime=xml.getText(cross, 'naturalTime'),
                    powerLawIndex=xml.getText(cross, 'powerLawIndex')),
                hershelBulkleyViscosity=HerschelBulkleyViscosity(
                    zeroShearViscosity=xml.getText(herSchelBulkley, 'zeroShearViscosity'),
                    yieldStressThreshold=xml.getText(herSchelBulkley, 'yieldStressThreshold'),
                    consistencyIndex=xml.getText(herSchelBulkley, 'consistencyIndex'),
                    powerLawIndex=xml.getText(herSchelBulkley, 'powerLawIndex')),
                carreauViscosity=CarreauViscosity(
                    zeroShearViscosity=xml.getText(carreau, 'zeroShearViscosity'),
                    infiniteShearViscosity=xml.getText(carreau, 'infiniteShearViscosity'),
                    relaxationTime=xml.getText(carreau, 'relaxationTime'),
                    powerLawIndex=xml.getText(carreau, 'powerLawIndex'),
                    linearityDeviation=xml.getText(carreau, 'linearityDeviation')),
                nonNewtonianPowerLawViscosity=NonNewtonianPowerLawViscosity(
                    maximumViscosity=xml.getText(nonNewtonianPowerLaw, 'maximumViscosity'),
                    minimumViscosity=xml.getText(nonNewtonianPowerLaw, 'minimumViscosity'),
                    consistencyIndex=xml.getText(nonNewtonianPowerLaw, 'consistencyIndex'),
                    powerLawIndex=xml.getText(nonNewtonianPowerLaw, 'powerLawIndex'))
            )

        return MaterialDefaults(specifications=Specifications(
                                    density=xml.getText(mixture, 'density/specification'),
                                    specificHeat=xml.getText(mixture, 'specificHeat/specification'),
                                    thermalConductivity=xml.getText(mixture, 'thermalConductivity/specification'),
                                    viscosity=xml.getText(mixture, 'viscosity/specification')
                                ),
                                viscosityProperties=viscosityProperties)