#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.material_db import IMaterialObserver, MaterialDB


USER_DEFINED_SCALAR_XPATH = 'models/userDefinedScalars/scalar'


class ScalarSpecificationMethod(Enum):
    CONSTANT = 'constant'
    TURBULENT_VISCOSITY = 'turbulentViscosity'
    LAMINAR_AND_TURBULENT_VISCOSITY = 'laminarAndTurbulentViscosity'


@dataclass
class UserDefinedScalar:
    scalarID: int
    fieldName: str
    region: int
    material: int
    specificationMethod: ScalarSpecificationMethod
    constantDiffusivity: str
    laminarViscosityCoefficient: str
    turbulentViscosityCoefficient: str


class UserDefinedScalarsDB:
    SCALAR_XPATH = 'models/userDefinedScalars'

    @classmethod
    def hasDefined(cls):
        return len(coredb.CoreDB().getUserDefinedScalars()) > 0

    @classmethod
    def getXPath(cls, scalarID):
        return f'{cls.SCALAR_XPATH}/scalar[@scalarID="{scalarID}"]'

    @classmethod
    def getFieldName(cls, scalarID):
        return coredb.CoreDB().getValue(f'{cls.SCALAR_XPATH}/scalar[@scalarID="{scalarID}"]/fieldName')

    @classmethod
    def getRegion(cls, scalarID):
        return coredb.CoreDB().getValue(f'{cls.SCALAR_XPATH}/scalar[@scalarID="{scalarID}"]/region')

    @classmethod
    def getUserDefinedScalar(cls, scalarID):
        db = coredb.CoreDB()
        xpath = cls.getXPath(scalarID)

        return UserDefinedScalar(
            scalarID=scalarID,
            fieldName=db.getValue(xpath + '/fieldName'),
            region=db.getValue(xpath + '/region'),
            material=db.getValue(xpath + '/material'),
            specificationMethod=ScalarSpecificationMethod(db.getValue(xpath + '/diffusivity/specificationMethod')),
            constantDiffusivity=db.getValue(xpath + '/diffusivity/constant'),
            laminarViscosityCoefficient=db.getValue(
                xpath + '/diffusivity/laminarAndTurbulentViscosity/laminarViscosityCoefficient'),
            turbulentViscosityCoefficient=db.getValue(
                xpath + '/diffusivity/laminarAndTurbulentViscosity/turbulentViscosityCoefficient')
        )

    @classmethod
    def isReferenced(cls, scalarID):
        return int(scalarID) and coredb.CoreDB().exists(f'monitors/*/*/field[field="scalar"][fieldID="{scalarID}"]')


class MaterialObserver(IMaterialObserver):
    def materialRemoving(self, db, mid: int):
        scalars = [xml.getText(e, 'fieldName') for e in db.getElements(f'{USER_DEFINED_SCALAR_XPATH}[material="{mid}"]')]
        if scalars:
            raise ConfigurationException(
                self.tr('{} is referenced by user-defined scalars {}').format(
                    MaterialDB.getName(mid), ' '.join(scalars)))
