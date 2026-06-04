#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import re
import yaml

import pandas as pd

from PySide6.QtCore import QCoreApplication

from libbaram.simple_db.simple_schema import TextType, FloatType, EnumType, SimpleArray
from libbaram.simple_db.simple_schema import validateData

from .constants import SpecificHeatSpecification
from .constants import DensitySpecification, MaterialType, Phase, TransportSpecification


commonSchema = {
    'name': TextType(),
    'aliases': SimpleArray(TextType()),
    'chemicalFormula': TextType(),

    # Constants
    'molecularWeight': FloatType(),
    'tripleTemperature': FloatType(),
    'triplePressure': FloatType(),
    'criticalTemperature': FloatType(),
    'criticalPressure': FloatType(),
    'criticalSpecificVolume': FloatType(),
    'normalBoilingTemperature': FloatType(),
    'acentricFactor': FloatType(),

    'sutherlandTemperature': FloatType(),
    'sutherlandCoefficient': FloatType(),

    'janafOld': {
        'lowTemperature': FloatType(),
        'commonTemperature': FloatType(),
        'highTemperature': FloatType(),
        'lowCoefficients': SimpleArray(FloatType().setDefault(0), 7),
        'highCoefficients': SimpleArray(FloatType().setDefault(0), 7)
    },

    'dipoleMoment': FloatType(),
    'solubilityParameter': FloatType(),

    # Temperature dependents
    # 101325Pa 298.15K
    'phase': EnumType(Phase),

    'saturationPressure': FloatType(),
    'enthalpyOfVaporization': FloatType(),

    'dropletSurfaceTension': FloatType(),
    'absorptionCoefficient': FloatType(),
    'emissivity': FloatType(),
}


liquidSchema = {
    'name': TextType(),
    'density': FloatType(),
    'specificHeat': FloatType(),
    'viscosity': FloatType(),
    'thermalConductivity': FloatType(),
    'standardStateEnthalpy': FloatType(),
    'referenceTemperature': FloatType(),
}


gasSchema = {
    'name': TextType(),
    'density': FloatType(),
    'specificHeat': FloatType(),
    'viscosity': FloatType(),
    'thermalConductivity': FloatType(),
    'standardStateEnthalpy': FloatType(),
    'referenceTemperature': FloatType(),
}


solidSchema = {
    'name': TextType(),
    'density': FloatType(),
    'specificHeat': FloatType(),
    'viscosity': FloatType(),
    'thermalConductivity': FloatType(),
}


def loadDatabase(path):
    with open(path) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)

    for name, values in data.items():
        if re.search(r'\s', name):
            raise ValueError(
                QCoreApplication.translate('MaterialBase', 'Material Name cannot include spaces - {}').format(name))

        data[name] = validateData(values, commonSchema, name)

        if liquid := values.get('liquid'):
            data[name]['liquid'] = validateData(liquid, liquidSchema, f'{name}/liquid')

        if gas := values.get('gas'):
            data[name]['gas'] = validateData(gas, gasSchema, f'{name}/gas')

        if solid := values.get('solid'):
            data[name]['solid'] = validateData(solid, solidSchema, f'{name}/solid')

    return data


def saveDatabase(path, data):
    with open(path, 'w') as file:
        yaml.dump(data, file, indent=4, sort_keys=False)


class Database:
    def __init__(self):
        self._path = None
        self._materials = None

        self._thermos: list[tuple[str, MaterialType, DensitySpecification, SpecificHeatSpecification, TransportSpecification]] = []

    def setPath(self, path):
        self._path = path

    def getMaterial(self, name):
        return self._materials[name]

    def getMaterials(self):
        return self._materials

    def getRawData(self):
        assert self._path is not None
        return loadDatabase(self._path)

    def getThermos(self):
        return self._thermos

    def load(self, path):
        self._path = path
        self._parse(loadDatabase(self._path))

    def update(self, rawData):
        saveDatabase(self._path, rawData)
        self.load(self._path)

    def validateThermos(
        self,
        materialType: MaterialType,
        phase: Phase,
        density: DensitySpecification,
        specificHeat: SpecificHeatSpecification,
        transport: TransportSpecification
    ) -> bool:
        if phase == Phase.SOLID:
            return ('heSolidThermo', materialType, density, specificHeat, transport) in self._thermos
        else:
            return ('heRhoThermo',   materialType, density, specificHeat, transport) in self._thermos

    def loadThermos(self, path: Path):
        # Read CSV without headers
        df = pd.read_csv(path, comment='#', header=None, names=['thermoType', 'mixture', 'equationOfState', 'thermo', 'transport'])

        for _, row in df.iterrows():
            try:
                mtype = MaterialType(row['mixture'])
                density = DensitySpecification(row['equationOfState'])
                specificHeat = SpecificHeatSpecification(row['thermo'])
                transport = TransportSpecification(row['transport'])

                self._thermos.append((row['thermoType'], mtype, density, specificHeat, transport))

            except ValueError as e:
                print(f"Warning: Skipping invalid row {row.to_dict()}: {e}")

    def _parse(self, rawData):
        materials = {}
        for key, m in rawData.items():
            m.pop('name')
            liquid = m.pop('liquid', None)
            gas = m.pop('gas', None)
            solid = m.pop('solid', None)

            # validateData(m, commonSchema)

            if liquid:
                # validateData(liquid, liquidSchema)
                liquid.update(m)
                liquid['phase'] = Phase.LIQUID
                materials[liquid['name']] = liquid

            if gas:
                # validateData(gas, gasSchema)
                gas.update(m)
                gas['phase'] = Phase.GAS
                materials[gas['name']] = gas

            if solid:
                # validateData(solid, solidSchema)
                solid.update(m)
                solid['phase'] = Phase.SOLID
                materials[solid['name']] = solid

        self._materials = materials


materialsBase = Database()
