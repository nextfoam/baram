#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import nsmap


UNIVERSAL_GAS_CONSTANT = 8314.46261815324  # J / ( K · kmol )

MATERIAL_XPATH = '/materials/material'


class Phase(Enum):
    GAS = 'gas'
    LIQUID = 'liquid'
    SOLID = 'solid'


class MaterialType(Enum):
    NONMIXTURE = 'nonmixture'
    MIXTURE = 'mixture'
    SPECIE = 'specie'


class SpecificHeatSpecification(Enum):
    CONSTANT = 'constant'
    POLYNOMIAL = 'polynomial'
    JANAF = 'janaf'
    TABLE = 'table'


class DensitySpecification(Enum):
    CONSTANT = 'constant'
    PERFECT_GAS = 'perfectGas'
    POLYNOMIAL = 'polynomial'
    INCOMPRESSIBLE_PERFECT_GAS = 'incompressiblePerfectGas'
    REAL_GAS_PENG_ROBINSON = 'PengRobinsonGas'
    BOUSSINESQ = 'boussinesq'
    PERFECT_FLUID = 'perfectFluid'
    TABLE = 'table'


class TransportSpecification(Enum):
    CONSTANT = 'constant'
    SUTHERLAND = 'sutherland'
    POLYNOMIAL = 'polynomial'
    CROSS_POWER_LAW = 'cross'
    HERSCHEL_BULKLEY = 'herschelBulkley'
    BIRD_CARREAU = 'carreau'
    POWER_LAW = 'nonNewtonianPowerLaw'
    TABLE = 'table'


NON_NEWTONIAN_VISCOSITY_SPECIFICATIONS = [TransportSpecification.CROSS_POWER_LAW,
                                          TransportSpecification.HERSCHEL_BULKLEY,
                                          TransportSpecification.BIRD_CARREAU,
                                          TransportSpecification.POWER_LAW]

@dataclass
class MaterialBase:
    mid: str
    name: str
    type: MaterialType
    phase: Phase


class Materials:
    def __init__(self):
        self._materials: dict[str, MaterialBase] = {}

    def load(self):
        self._materials.clear()

        for e in coredb.CoreDB().getElements(MATERIAL_XPATH):
            mid = e.get('mid')
            self._materials[mid] = MaterialBase(mid=mid,
                                                name=e.find('name', namespaces=nsmap).text,
                                                type=MaterialType(e.find('type', namespaces=nsmap).text),
                                                phase=Phase(e.find('phase', namespaces=nsmap).text))

    def getMaterials(self, types=None, phases=None):
        return [m for m in self._materials.values()
                if (types is None or m.type in types) and (phases is None or m.phase in phases)]

    def getMaterial(self, mid):
        return self._materials[mid]


class MaterialManager:
    @staticmethod
    def loadMaterials() -> Materials:
        materials = Materials()
        materials.load()

        return materials
