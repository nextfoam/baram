#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from xml.sax.saxutils import escape

import pandas as pd

from resources import resource


MATERIALS_PATH = 'materials.csv'


_MIXTURE_VALUES = {
    'CoolPropName': 'Mixture',
    'chemicalFormula': None,
    'phase': None,
    'molecularWeight': None,
    'density': 0,
    'viscosity': 1,
    'thermalConductivity': 0,
    'specificHeat': 0,
    'emissivity': None,
    'absorptionCoefficient': None,
    'sutherlandTemperature': 0,
    'sutherlandCoefficient': 0,
    'surfaceTension': None,
    'saturationPressure': None,
    'criticalTemperature': None,
    'criticalPressure': None,
    'criticalDensity': None,
    'acentricFactor': None
}


def _propertyElement(name,value):
    return '' if value is None else f"<{name}>{value}</{name}>"


def _pengRobinsonXML(values):
    return ("<pengRobinsonParameters>"
            f"  <criticalTemperature>{values['criticalTemperature']}</criticalTemperature>"
            f"  <criticalPressure>{values['criticalPressure']}</criticalPressure>"
            f"  <criticalSpecificVolume>{round(1 / float(values['criticalDensity']), 4)}</criticalSpecificVolume>"
            f"  <acentricFactor>{values['acentricFactor']}</acentricFactor>"
            "</pengRobinsonParameters>")


def _viscosityXML(phase, values):
    def sutherland(values):
        return ("<sutherland>"
                f"  <coefficient>{values['sutherlandCoefficient']}</coefficient>"
                f"  <temperature>{values['sutherlandTemperature']}</temperature>"
                "</sutherland>")

    return ("<viscosity>"
            "   <specification>constant</specification>"
            f"  <constant>{values['viscosity']}</constant>"
            "   <polynomial>0</polynomial>"
            f"  {sutherland(values) if phase == 'gas' else ''}"
            "</viscosity>")


class MaterialTemplates:
    @dataclass
    class Specifications:
        type: str = 'nonmixture'
        phase: str = None   # Only for mixture

        density: str = 'constant'
        specificHeat: str = 'constant'
        thermalConductivity: str = 'constant'
        viscosity: str = 'constant'

    MIXTURE_TEMPLATE_NAME = 'MIXTURE'
    DEFAULT_NONMIXTURE_SPEC = Specifications()
    DEFAULT_SPECIE_SPEC = Specifications('specie')

    def __init__(self):
        self._materials = None

        df = pd.read_csv(resource.file(MATERIALS_PATH), header=0, index_col=0).transpose()
        self._materials = df.where(pd.notnull(df), None).to_dict()
        self._materials[self.MIXTURE_TEMPLATE_NAME] = _MIXTURE_VALUES

    def template(self, name):
        return self._materials[name]

    def getMaterials(self, phase=None) -> list[(str, str, str)]:
        """Returns available materials from material database

        Returns available materials with name, chemicalFormula and phase from material database

        Returns:
            List of materials in tuple, '(name, chemicalFormula, phase)'
        """
        if phase:
            return [(k, v['chemicalFormula'], v['phase']) for k, v in self._materials.items() if v['phase'] == phase]

        return [(k, v['chemicalFormula'], v['phase'])
                for k, v in self._materials.items() if k != self.MIXTURE_TEMPLATE_NAME]

    def materialXML(self, mid, name, templateName, specifications, typeXML=None):
        values = self._materials[templateName]
        type_ = specifications.type
        phase = specifications.phase if type_ == 'mixture' else values['phase']
        chemicalFormula = (f"<chemicalFormula>{escape(values['chemicalFormula'])}</chemicalFormula>"
                           if values['chemicalFormula'] else '')

        xml = f'''
            <material mid="{mid}" xmlns="http://www.baramcfd.org/baram">
                <name>{name}</name>
                <type>{type_}</type>
                {chemicalFormula}
                <phase>{phase}</phase>
                {_propertyElement('molecularWeight', values['molecularWeight'])}
                {_propertyElement('absorptionCoefficient', values['absorptionCoefficient'])}
                {_propertyElement('saturationPressure', values['saturationPressure'])}
                {_propertyElement('emissivity', values['emissivity'])}
                <density>
                    <specification>{specifications.density}</specification>
                    <constant>{values['density']}</constant>
                    <polynomial>0</polynomial>
                    {_pengRobinsonXML(values) if type_ != 'mixture' and phase == 'gas' else ''}
                </density>
                <specificHeat>
                    <specification>{specifications.specificHeat}</specification>
                    <constant>{values['specificHeat']}</constant>
                    <polynomial>0</polynomial>
                </specificHeat>
                {'' if phase == 'solid' else _viscosityXML(phase, values)}
                <thermalConductivity>
                    <specification>{specifications.thermalConductivity}</specification>
                    <constant>{values['thermalConductivity']}</constant>
                    <polynomial>0</polynomial>
                </thermalConductivity>
                {'' if typeXML is None else typeXML}
            </material>
        '''

        return xml

    _MIXTURE_XML = '<mixture><massDiffusivity>1e-10</massDiffusivity><primarySpecie>0</primarySpecie></mixture>'

    def mixtureXML(self):
        return self._MIXTURE_XML

    def specieXML(self, mxtureID):
        return f'<specie><mixture>{mxtureID}</mixture></specie>'



