#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Flag, auto

from PySide6.QtCore import QCoreApplication

from coredb import coredb


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
    def getPhase(cls, mid) -> Phase:
        return cls.dbTextToPhase(coredb.CoreDB().getValue(cls.getXPath(mid) + '/phase'))

    @classmethod
    def getCoolPropName(cls, mid) -> str:
        name = coredb.CoreDB().getValue(f'{MaterialDB.getXPath(mid)}/name')
        return coredb.CoreDB().materialDB[name]['CoolPropName']

    @classmethod
    def getDensity(cls, mid, t: float, p: float) -> float:
        spec = coredb.CoreDB().getValue(cls.getXPath(mid) + '/density/specification')
        if spec == 'constant':
            return float(coredb.CoreDB().getValue(cls.getXPath(mid) + '/density/constant'))
        elif spec == 'perfectGas':
            mw = float(coredb.CoreDB().getValue(cls.getXPath(mid) + '/molecularWeight'))
            return p * mw / (8.31446261815324 * t)
        else:
            raise KeyError

    @classmethod
    def getSpecificHeat(cls, mid: int, t: float) -> float:
        spec = coredb.CoreDB().getValue(cls.getXPath(mid) + '/specificHeat/specification')
        if spec == 'constant':
            return float(coredb.CoreDB().getValue(cls.getXPath(mid) + '/specificHeat/constant'))
        elif spec == 'polynomial':
            coeffs = list(map(float, coredb.CoreDB().getValue(cls.getXPath(mid) + '/specificHeat/polynomial').split()))
            cp = 0.0
            exp = 0
            for c in coeffs:
                cp += c * t ** exp
                exp += 1
            return cp
        else:
            raise KeyError

    @classmethod
    def getViscosity(cls, mid: int, t: float) -> float:
        spec = coredb.CoreDB().getValue(cls.getXPath(mid) + '/viscosity/specification')
        if spec == 'constant':
            return float(coredb.CoreDB().getValue(cls.getXPath(mid) + '/viscosity/constant'))
        elif spec == 'polynomial':
            coeffs = list(map(float, coredb.CoreDB().getValue(cls.getXPath(mid) + '/viscosity/polynomial').split()))
            cp = 0.0
            exp = 0
            for c in coeffs:
                cp += c * t ** exp
                exp += 1
            return cp
        elif spec == 'sutherland':
            c1 = float(coredb.CoreDB().getValue(cls.getXPath(mid) + '/viscosity/sutherland/coefficient'))
            s = float(coredb.CoreDB().getValue(cls.getXPath(mid) + '/viscosity/sutherland/temperature'))
            return c1 * t ** 1.5 / (t+s)
        else:
            raise KeyError

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
