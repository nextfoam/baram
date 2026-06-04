#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from xml.etree.ElementTree import Element
from xml.sax.saxutils import escape

from libbaram.pfloat import PFloat

from baramFlow.base.base import Function1Scalar
from baramFlow.coredb.libdb import nsmap, E
from .constants import MaterialType, Phase
from .density import Density
from .specific_heat import SpecificHeat
from .transport import Transport


@dataclass
class MixtureProperties:
    massDiffusivity: PFloat = field(default_factory=lambda: PFloat('1e-10'))
    primarySpecieID: str    = ''

    @staticmethod
    def fromElement(e: Element):
        if e is None:
            return None

        return MixtureProperties(massDiffusivity=PFloat.fromElement(e.find('massDiffusivity', namespaces=nsmap)),
                                 primarySpecieID=e.find('primarySpecie', namespaces=nsmap).text)

    def toElement(self):
        return E('mixture',
                 self.massDiffusivity.toElement('massDiffusivity'),
                 E('primarySpecie', self.primarySpecieID))

@dataclass
class SpecieProperties:
    mixtureID: str

    @staticmethod
    def fromElement(e: Element):
        if e is None:
            return None

        return SpecieProperties(mixtureID=e.find('mixture', namespaces=nsmap).text)

    def toElement(self):
        return E('specie',
                 E('mixture', self.mixtureID))


@dataclass(kw_only=True)
class MaterialBase:
    mid: str
    name: str
    type: MaterialType
    phase: Phase


@dataclass(kw_only=True)
class Material(MaterialBase):
    chemicalFormula: str                        = ''
    density: Density                            = field(default_factory=Density)
    specificHeat: SpecificHeat                  = field(default_factory=SpecificHeat)
    transport: Transport
    molecularWeight: PFloat | None              = None
    criticalTemperature: PFloat | None          = None
    criticalPressure: PFloat | None             = None
    criticalSpecificVolume: PFloat | None       = None
    tripleTemperature: PFloat | None            = None
    triplePressure: PFloat | None               = None
    normalBoilingTemperature: PFloat | None     = None
    standardStateEnthalpy: PFloat | None        = None
    referenceTemperature: PFloat | None         = None
    acentricFactor: PFloat | None               = None
    saturationPressure: Function1Scalar         = None
    enthalpyOfVaporization: Function1Scalar     = None
    dropletSurfaceTension: Function1Scalar      = None
    absorptionCoefficient: PFloat | None        = None
    emissivity: PFloat | None                   = None
    mixtureProperties: MixtureProperties | None = None
    specieProperties: SpecieProperties | None   = None

    @staticmethod
    def fromElement(e: Element):
        chemicalFormula=e.find('chemicalFormula', namespaces=nsmap)
        molecularWeight=e.find('molecularWeight', namespaces=nsmap)
        criticalTemperature=e.find('criticalTemperature', namespaces=nsmap)
        criticalPressure=e.find('criticalPressure', namespaces=nsmap)
        criticalSpecificVolume=e.find('criticalSpecificVolume', namespaces=nsmap)
        tripleTemperature=e.find('tripleTemperature', namespaces=nsmap)
        triplePressure=e.find('triplePressure', namespaces=nsmap)
        normalBoilingTemperature=e.find('normalBoilingTemperature', namespaces=nsmap)
        standardStateEnthalpy=e.find('standardStateEnthalpy', namespaces=nsmap)
        referenceTemperature=e.find('referenceTemperature', namespaces=nsmap)
        acentricFactor=e.find('acentricFactor', namespaces=nsmap)
        saturationPressure=e.find('saturationPressure', namespaces=nsmap)
        enthalpyOfVaporization=e.find('enthalpyOfVaporization', namespaces=nsmap)
        dropletSurfaceTension=e.find('dropletSurfaceTension', namespaces=nsmap)
        absorptionCoefficient=e.find('absorptionCoefficient', namespaces=nsmap)
        emissivity=e.find('emissivity', namespaces=nsmap)

        return Material(
            mid=e.get('mid'),
            name=e.find('name', namespaces=nsmap).text,
            type=MaterialType(e.find('type', namespaces=nsmap).text),
            phase=Phase(e.find('phase', namespaces=nsmap).text),
            chemicalFormula='' if chemicalFormula is None else chemicalFormula.text,
            density=Density.fromElement(e.find('density', namespaces=nsmap)),
            specificHeat=SpecificHeat.fromElement(e.find('specificHeat', namespaces=nsmap)),
            transport=Transport.fromElement(e.find('transport', namespaces=nsmap)),
            molecularWeight=None if molecularWeight is None else PFloat.fromElement(molecularWeight),
            criticalTemperature=None if criticalTemperature is None else PFloat.fromElement(criticalTemperature),
            criticalPressure=None if criticalPressure is None else PFloat.fromElement(criticalPressure),
            criticalSpecificVolume=(None if criticalSpecificVolume is None
                                    else PFloat.fromElement(criticalSpecificVolume)),
            tripleTemperature=None if tripleTemperature is None else PFloat.fromElement(tripleTemperature),
            triplePressure=None if triplePressure is None else PFloat.fromElement(triplePressure),
            normalBoilingTemperature=(None if normalBoilingTemperature is None
                                      else PFloat.fromElement(normalBoilingTemperature)),
            standardStateEnthalpy=None if standardStateEnthalpy is None else PFloat.fromElement(standardStateEnthalpy),
            referenceTemperature=None if referenceTemperature is None else PFloat.fromElement(referenceTemperature),
            acentricFactor=None if acentricFactor is None else PFloat.fromElement(acentricFactor),
            saturationPressure=None if saturationPressure is None else Function1Scalar.fromElement(saturationPressure),
            enthalpyOfVaporization=(None if enthalpyOfVaporization is None
                                    else Function1Scalar.fromElement(enthalpyOfVaporization)),
            dropletSurfaceTension=(None if dropletSurfaceTension is None
                                   else Function1Scalar.fromElement(dropletSurfaceTension)),
            absorptionCoefficient=None if absorptionCoefficient is None else PFloat.fromElement(absorptionCoefficient),
            emissivity=None if emissivity is None else PFloat.fromElement(emissivity),
            mixtureProperties=MixtureProperties.fromElement(e.find('mixture', namespaces=nsmap)),
            specieProperties=SpecieProperties.fromElement(e.find('specie', namespaces=nsmap)))

    def toElement(self):
        elements = [
            E('name', self.name),
            E('type', self.type),
            E('phase', self.phase),
            E('chemicalFormula', self.chemicalFormula),
            self.density.toElement(),
            self.specificHeat.toElement(),
            self.transport.toElement()]

        if self.molecularWeight is not None:
            elements.append(self.molecularWeight.toElement('molecularWeight'))

        if self.criticalTemperature is not None:
            elements.append(self.criticalTemperature.toElement('criticalTemperature'))

        if self.criticalPressure is not None:
            elements.append(self.criticalPressure.toElement('criticalPressure'))

        if self.criticalSpecificVolume is not None:
            elements.append(self.criticalSpecificVolume.toElement('criticalSpecificVolume'))

        if self.tripleTemperature is not None:
            elements.append(self.tripleTemperature.toElement('tripleTemperature'))

        if self.triplePressure is not None:
            elements.append(self.triplePressure.toElement('triplePressure'))

        if self.normalBoilingTemperature is not None:
            elements.append(self.normalBoilingTemperature.toElement('normalBoilingTemperature'))

        if self.standardStateEnthalpy is not None:
            elements.append(self.standardStateEnthalpy.toElement('standardStateEnthalpy'))

        if self.referenceTemperature is not None:
            elements.append(self.referenceTemperature.toElement('referenceTemperature'))

        if self.acentricFactor is not None:
            elements.append(self.acentricFactor.toElement('acentricFactor'))

        if self.saturationPressure:
            elements.append(self.saturationPressure.toElement('saturationPressure'))

        if self.enthalpyOfVaporization is not None:
            elements.append(self.enthalpyOfVaporization.toElement('enthalpyOfVaporization'))

        if self.dropletSurfaceTension is not None:
            elements.append(self.dropletSurfaceTension.toElement('dropletSurfaceTension'))

        if self.absorptionCoefficient is not None:
            elements.append(self.absorptionCoefficient.toElement('absorptionCoefficient'))

        if self.emissivity is not None:
            elements.append(self.emissivity.toElement('emissivity'))

        if self.mixtureProperties is not None:
            elements.append(self.mixtureProperties.toElement())

        if self.specieProperties is not None:
            elements.append(self.specieProperties.toElement())

        return E('material',
                 *[e for e in elements if e is not None],
                 mid=self.mid)


def createMixture(mid: str, name: str, phase: Phase):
    base = {
        'chemicalFormula': '',
        'phase': phase,
        'density': '0',
        'viscosity': '1',
        'thermalConductivity': '0',
        'specificHeat': '0',
        'sutherlandTemperature': '0',
        'sutherlandCoefficient': '0',
        'criticalTemperature': '298.15',
        'criticalPressure': '101325',
        'criticalSpecificVolume': '1',
        'tripleTemperature': '298.15',
        'triplePressure': '101325',
        'normalBoilingTemperature': '298.15',
        'standardStateEnthalpy': '0',
        'referenceTemperature': '298.15',
        'acentricFactor': '0',
        'saturationPressure': '101325',
        'enthalpyOfVaporization': '0',
        'dropletSurfaceTension': '0.00001',
    }

    return _createMaterial(mid, name, MaterialType.MIXTURE, base)


def createSpecie(mid: str, name: str, base: dict, mixture: Material):
    specie = createNonMixture(mid, name, base)
    specie.type = MaterialType.SPECIE

    specie.density.specification = mixture.density.specification
    specie.specificHeat.specification = mixture.specificHeat.specification

    specie.transport.specification = mixture.transport.specification
    specie.transport.crossPowerLaw = mixture.transport.crossPowerLaw
    specie.transport.herschelBulkley = mixture.transport.herschelBulkley
    specie.transport.birdCarreau = mixture.transport.birdCarreau
    specie.transport.nonNewtonianPowerLaw = mixture.transport.nonNewtonianPowerLaw

    specie.specieProperties = SpecieProperties(mixtureID=mixture.mid)

    return specie


def createNonMixture(mid: str, name: str, base: dict):
    return _createMaterial(mid, name, MaterialType.NONMIXTURE, base)


def _createMaterial(mid: str, name: str, type: MaterialType, base: dict):
    phase = Phase(base['phase'])

    return Material(
        mid=mid,
        name=name,
        type=type,
        phase=base['phase'],
        chemicalFormula=escape(base['chemicalFormula']) if base.get('chemicalFormula', None) else '',
        density=Density.default(base['density'], phase, type),
        specificHeat=SpecificHeat(constant=PFloat(base['specificHeat'])),
        transport=Transport.fromBase(base, phase),
        molecularWeight=None if type == MaterialType.MIXTURE else PFloat(base['molecularWeight']),
        criticalTemperature=PFloat(base['criticalTemperature']),
        criticalPressure=PFloat(base['criticalPressure']),
        criticalSpecificVolume=PFloat(base['criticalSpecificVolume']),
        tripleTemperature=PFloat(base['tripleTemperature']),
        triplePressure=PFloat(base['triplePressure']),
        normalBoilingTemperature=PFloat(base['normalBoilingTemperature']),
        standardStateEnthalpy=None if phase == Phase.SOLID else PFloat(base['standardStateEnthalpy']),
        referenceTemperature =None if phase == Phase.SOLID else PFloat(base['referenceTemperature']),
        acentricFactor=PFloat(base['acentricFactor']),
        saturationPressure=Function1Scalar(constant=PFloat(base['saturationPressure'])),
        enthalpyOfVaporization=Function1Scalar(constant=PFloat(base['enthalpyOfVaporization'])),
        dropletSurfaceTension=Function1Scalar(constant=PFloat(base['dropletSurfaceTension'])),
        absorptionCoefficient=None if type == MaterialType.MIXTURE else PFloat(base['absorptionCoefficient']),
        emissivity=None if type == MaterialType.MIXTURE else PFloat(base['emissivity']))


