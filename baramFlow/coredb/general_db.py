#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb
from baramFlow.coredb.scalar_model_db import IUserDefinedScalarObserver


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


class ScalarObserver(IUserDefinedScalarObserver):
    ABL_SCALARS_XPATH = GeneralDB.GENERAL_XPATH + '/atmosphericBoundaryLayer/userDefinedScalars'

    def scalarAdded(self, db, scalarID):
        atmosphericBoundaryLayerScalars = db.getElement(self.ABL_SCALARS_XPATH)

        atmosphericBoundaryLayerScalars.append(xml.createElement('<scalar xmlns="http://www.baramcfd.org/baram">'
                                                                 f' <scalarID>{scalarID}</scalarID>'
                                                                 '  <value>0</value>'
                                                                 '</scalar>'))

    def scalarRemoving(self, db, scalarID):
        xml.removeElement(db.getElement(self.ABL_SCALARS_XPATH), f'scalar[scalarID="{scalarID}"]')

    def scalarsCleared(self, db):
        db.clearElement(self.ABL_SCALARS_XPATH)

