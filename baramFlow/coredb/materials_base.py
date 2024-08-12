#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd

from resources import resource


MATERIALS_PATH = 'materials.csv'


class MaterialsBase:
    _materials = None
    _mixture = {
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

    @classmethod
    def load(cls):
        df = pd.read_csv(resource.file(MATERIALS_PATH), header=0, index_col=0).transpose()
        cls._materials = df.where(pd.notnull(df), None).to_dict()

    @classmethod
    def getMaterial(cls, name):
        return cls._materials[name]

    @classmethod
    def getMixture(cls):
        return cls._mixture

    @classmethod
    def getMaterials(cls, phase=None) -> list[(str, str, str)]:
        """Returns available materials from material database

        Returns available materials with name, chemicalFormula and phase from material database

        Returns:
            List of materials in tuple, '(name, chemicalFormula, phase)'
        """
        if phase:
            return [(k, v['chemicalFormula'], v['phase']) for k, v in cls._materials.items() if v['phase'] == phase]

        return [(k, v['chemicalFormula'], v['phase']) for k, v in cls._materials.items()]


MaterialsBase.load()
