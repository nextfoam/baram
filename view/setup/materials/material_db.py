#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from enum import Enum, Flag, auto

MATERIALS_XPATH = './/materials'

_mutex = Lock()


class ListIndex(Enum):
    ID = 0
    NAME = auto()
    CHEMICAL_FORMULAR = auto()
    PHASE = auto()


class DBListIndex(Enum):
    NAME = 0
    CHEMICAL_FORMULAR = auto()
    PHASE = auto()


class Phase(Flag):
    GAS = auto()
    LIQUID = auto()
    SOLID = auto()
    FLUID = GAS | LIQUID


class Specification(Flag):
    CONSTANT = "constant"
    PERFECT_GAS = "perfectGas"
    SUTHERLAND = "sutherland"
    POLYNOMIAL = "polynomial"


class MaterialDB(object):
    specificationText = {
        Specification.CONSTANT: "Constant",
        Specification.PERFECT_GAS: "Perfect Gas",
        Specification.SUTHERLAND: "Sutherland",
        Specification.POLYNOMIAL: "Polynomial"
    }

    phaseText = {
        Phase.GAS: "Gas",
        Phase.LIQUID: "Liquid",
        Phase.SOLID: "Solid"
    }

    @classmethod
    def getXPath(cls, mid):
        return f'{MATERIALS_XPATH}/material[@mid="{mid}"]'

    @classmethod
    def getPhase(cls, dbText):
        if dbText == "gas":
            return Phase.GAS
        elif dbText == "liquid":
            return Phase.LIQUID
        elif dbText == "solid":
            return Phase.SOLID
        
    @classmethod
    def getPhaseText(cls, phase):
        return cls.phaseText[phase]

    @classmethod
    def getSpecification(cls, dbText):
        return Specification(dbText)

    @classmethod
    def getSpecificationText(cls, specifcation):
        return cls.specificationText[specifcation]
