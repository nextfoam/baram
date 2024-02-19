#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Flag, auto

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb import coredb

UNIVERSAL_GAL_CONSTANT = 8314.46261815324


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
    def getXPath(cls, mid) -> str:
        return f'{cls.MATERIALS_XPATH}/material[@mid="{mid}"]'

    @classmethod
    def getName(cls, mid):
        return coredb.CoreDB().getValue(cls.getXPath(mid) + '/name')

    @classmethod
    def getPhase(cls, mid) -> Phase:
        return cls.dbTextToPhase(coredb.CoreDB().getValue(cls.getXPath(mid) + '/phase'))

    @classmethod
    def getCoolPropName(cls, mid) -> str:
        name = coredb.CoreDB().getValue(f'{MaterialDB.getXPath(mid)}/name')
        return coredb.CoreDB().materialDB[name]['CoolPropName']

    @classmethod
    def dbTextToPhase(cls, DBText) -> Phase:
        if DBText == "gas":
            return Phase.GAS
        elif DBText == "liquid":
            return Phase.LIQUID
        elif DBText == "solid":
            return Phase.SOLID
        
    @classmethod
    def getPhaseText(cls, phase) -> str:
        return cls._phaseText[phase]

    @classmethod
    def dbSpecificationToText(cls, DBText) -> str:
        return cls.specificationText[Specification(DBText)]

    @classmethod
    def isMaterialExists(cls, name) -> bool:
        return coredb.CoreDB().exists(f'{cls.MATERIALS_XPATH}/material[name="{name}"]')

    @classmethod
    def isFluid(cls, mid):
        return coredb.CoreDB().getValue(cls.getXPath(mid) + '/phase') != Phase.SOLID.value
