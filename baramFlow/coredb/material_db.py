#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, Flag

from PySide6.QtCore import QCoreApplication

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb

UNIVERSAL_GAS_CONSTANT = 8314.46261815324


class Phase(Flag):
    GAS = 'gas'
    LIQUID = 'liquid'
    SOLID = 'solid'


class Specification(Enum):
    CONSTANT = 'constant'
    PERFECT_GAS = 'perfectGas'
    SUTHERLAND = 'sutherland'
    POLYNOMIAL = 'polynomial'
    INCOMPRESSIBLE_PERFECT_GAS = 'incompressiblePerfectGas'
    REAL_GAS_PENG_ROBINSON = 'PengRobinsonGas'


class MaterialType(Enum):
    NONMIXTURE = 'nonmixture'
    MIXTURE = 'mixture'
    SPECIE = 'specie'


class MaterialDB(object):
    MATERIALS_XPATH = 'materials'

    @classmethod
    def getXPath(cls, mid) -> str:
        return f'{cls.MATERIALS_XPATH}/material[@mid="{mid}"]'

    @classmethod
    def getXPathByName(cls, name) -> str:
        return f'{cls.MATERIALS_XPATH}/material[name="{name}"]'

    @classmethod
    def getName(cls, mid):
        return coredb.CoreDB().getValue(cls.getXPath(mid) + '/name')

    @classmethod
    def getPhase(cls, mid) -> Phase:
        return Phase(coredb.CoreDB().getValue(cls.getXPath(mid) + '/phase'))

    @classmethod
    def getType(cls, mid):
        return MaterialType(coredb.CoreDB().getValue(cls.getXPath(mid) + '/type'))

    @classmethod
    def getCoolPropName(cls, mid) -> str:
        name = coredb.CoreDB().getValue(f'{MaterialDB.getXPath(mid)}/name')
        return coredb.CoreDB().materialDB[name]['CoolPropName']

    @classmethod
    def dbTextToPhase(cls, DBText) -> Phase:
        if DBText == 'gas':
            return Phase.GAS
        elif DBText == 'liquid':
            return Phase.LIQUID
        elif DBText == 'solid':
            return Phase.SOLID
        
    @classmethod
    def getPhaseText(cls, phase) -> str:
        return {
            Phase.GAS:      QCoreApplication.translate('MaterialDB', 'Gas'),
            Phase.LIQUID:   QCoreApplication.translate('MaterialDB', 'Liquid'),
            Phase.SOLID:    QCoreApplication.translate('MaterialDB', 'Solid')
        }.get(phase)

    @classmethod
    def specificationToText(cls, specification) -> str:
        return {
            Specification.CONSTANT:                     QCoreApplication.translate('MaterialDB', 'Constant'),
            Specification.PERFECT_GAS:                  QCoreApplication.translate('MaterialDB', 'Perfect Gas'),
            Specification.SUTHERLAND:                   QCoreApplication.translate('MaterialDB', 'Sutherland'),
            Specification.POLYNOMIAL:                   QCoreApplication.translate('MaterialDB', 'Polynomial'),
            Specification.INCOMPRESSIBLE_PERFECT_GAS:   QCoreApplication.translate('MaterialDB',
                                                                                   'Incompressible-perfect-gas'),
            Specification.REAL_GAS_PENG_ROBINSON:       QCoreApplication.translate('MaterialDB',
                                                                                   'Real-gas-peng-robinson'),
        }.get(Specification(specification))

    @classmethod
    def dbSpecificationToText(cls, DBText) -> str:
        return cls.specificationToText(Specification(DBText))

    @classmethod
    def isMaterialExists(cls, name) -> bool:
        return coredb.CoreDB().exists(f'{cls.MATERIALS_XPATH}/material[name="{name}"]')

    @classmethod
    def isFluid(cls, mid):
        return cls.getPhase(mid) != Phase.SOLID

    @classmethod
    def getMaterialComposition(cls, xpath, mid):
        if MaterialDB.getType(mid) == MaterialType.MIXTURE:
            return [(xml.getText('mid', e), float(xml.getText('value', e)))
                    for e in coredb.CoreDB().getElements(f'{xpath}/mixture[mid="{mid}"]/specie')]

        return [(mid, 1)]