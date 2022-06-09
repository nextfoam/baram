#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, Flag, auto

from PySide6.QtCore import QCoreApplication


MATERIALS_XPATH = './/materials'


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
    _specificationText = {
        Specification.CONSTANT:    QCoreApplication.translate("MaterialDB", "Constant"),
        Specification.PERFECT_GAS: QCoreApplication.translate("MaterialDB", "Perfect Gas"),
        Specification.SUTHERLAND:  QCoreApplication.translate("MaterialDB", "Sutherland"),
        Specification.POLYNOMIAL:  QCoreApplication.translate("MaterialDB", "Polynomial"),
    }

    _phaseText = {
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
        return cls._phaseText[phase]

    @classmethod
    def getSpecification(cls, dbText):
        return Specification(dbText)

    @classmethod
    def getSpecificationText(cls, specifcation):
        return cls._specificationText[specifcation]
