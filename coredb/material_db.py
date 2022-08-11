#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, Flag, auto

from PySide6.QtCore import QCoreApplication

from coredb import coredb


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
    MATERIALS_XPATH = './/materials'

    specificationText = {
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
        return f'{cls.MATERIALS_XPATH}/material[@mid="{mid}"]'

    @classmethod
    def getPhase(cls, mid):
        return cls.dbTextToPhase(coredb.CoreDB().getValue(cls.getXPath(mid) + '/phase'))

    @classmethod
    def dbTextToPhase(cls, DBText):
        if DBText == "gas":
            return Phase.GAS
        elif DBText == "liquid":
            return Phase.LIQUID
        elif DBText == "solid":
            return Phase.SOLID
        
    @classmethod
    def getPhaseText(cls, phase):
        return cls._phaseText[phase]

    @classmethod
    def dbSpecificationToText(cls, DBText):
        return cls.specificationText[Specification(DBText)]

    @classmethod
    def isMaterialExists(cls, name):
        return coredb.CoreDB().exists(f'{cls.MATERIALS_XPATH}/material[name="{name}"]')
