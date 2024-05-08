#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from baramFlow.coredb import coredb


class SolverType(Enum):
    PRESSURE_BASED = 'pressureBased'
    DENSITY_BASED = 'densityBased'


class GeneralDB:
    GENERAL_XPATH = './/general'
    OPERATING_CONDITIONS_XPATH = './/operatingConditions'

    @classmethod
    def isTimeTransient(cls):
        return coredb.CoreDB().getValue(cls.GENERAL_XPATH + '/timeTransient') == 'true'

    @classmethod
    def isCompressible(cls):
        return coredb.CoreDB().getValue(cls.GENERAL_XPATH + '/flowType') == 'compressible'

    @classmethod
    def getSolverType(cls):
        return SolverType(coredb.CoreDB().getValue(cls.GENERAL_XPATH + '/solverType'))

    @classmethod
    def isDensityBased(cls):
        return cls.getSolverType() == SolverType.DENSITY_BASED

    @classmethod
    def isPressureBased(cls):
        return cls.getSolverType() == SolverType.PRESSURE_BASED

    @classmethod
    def isCompressibleDensity(cls):
        return cls.isCompressible() and cls.isDensityBased()
