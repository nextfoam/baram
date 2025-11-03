#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import nsmap

MATERIAL_XPATH = '/materials/material'


class Phase(Enum):
    GAS = 'gas'
    LIQUID = 'liquid'
    SOLID = 'solid'


class MaterialType(Enum):
    NONMIXTURE = 'nonmixture'
    MIXTURE = 'mixture'
    SPECIE = 'specie'


@dataclass
class MaterialBase:
    mid: str
    name: str
    type: MaterialType
    phase: Phase


class Materials:
    def __init__(self):
        self._materials = None

    def load(self):
        self._materials = []

        for e in coredb.CoreDB().getElements(MATERIAL_XPATH):
            self._materials.append(MaterialBase(mid=e.get('mid'),
                                                name=e.find('name', namespaces=nsmap).text,
                                                type=MaterialType(e.find('type', namespaces=nsmap).text),
                                                phase=Phase(e.find('phase', namespaces=nsmap).text)))

    def getMaterials(self, types=None, phases=None):
        return [
            m for m in self._materials if (types is None or m.type in types) and (phases is None or m.phase in phases)]


class MaterialManager:
    @staticmethod
    def loadMaterials():
        materials = Materials()
        materials.load()

        return materials