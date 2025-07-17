#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd


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
    def load(cls, file):
        df = pd.read_csv(file, header=0, index_col=0, dtype=str).transpose()
        cls._materials = df.where(pd.notnull(df), None).to_dict()

    @classmethod
    def update(cls, materials):
        cls._materials = materials

    @classmethod
    def getMaterial(cls, name):
        return cls._materials[name]

    @classmethod
    def getMixture(cls):
        return cls._mixture

    @classmethod
    def getMaterials(cls):
        return cls._materials
