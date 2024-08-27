#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QObject

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.material_db import IMaterialObserver, MaterialDB


USER_DEFINED_SCALAR_XPATH = 'models/userDefinedScalars/scalar'


class ScalarSpecificationMethod(Enum):
    CONSTANT = 'constant'
    # TURBULENT_VISCOSITY = 'turbulentViscosity'
    LAMINAR_AND_TURBULENT_VISCOSITY = 'laminarAndTurbulentViscosity'


@dataclass
class UserDefinedScalar:
    scalarID: int
    fieldName: str
    rname: str
    material: str
    specificationMethod: ScalarSpecificationMethod
    constantDiffusivity: str
    laminarViscosityCoefficient: str
    turbulentViscosityCoefficient: str


class IUserDefinedScalarObserver(QObject):
    def scalarAdded(self, db, scalarID):
        pass

    def scalarRemoving(self, db, scalarID):
        pass


def _rootElement():
    return coredb.CoreDB().getElement(UserDefinedScalarsDB.SCALAR_XPATH)


class UserDefinedScalarsDB:
    SCALAR_XPATH = 'models/userDefinedScalars'

    _observers = []

    @classmethod
    def registerObserver(cls, observer):
        cls._observers.append(observer)

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
    def getUserDefinedScalar(cls, scalarID) -> UserDefinedScalar:
        db = coredb.CoreDB()
        xpath = cls.getXPath(scalarID)

        return UserDefinedScalar(
            scalarID=scalarID,
            fieldName=db.getValue(xpath + '/fieldName'),
            rname=db.getValue(xpath + '/region'),
            material=db.getValue(xpath + '/material'),
            specificationMethod=ScalarSpecificationMethod(db.getValue(xpath + '/diffusivity/specificationMethod')),
            constantDiffusivity=db.getValue(xpath + '/diffusivity/constant'),
            laminarViscosityCoefficient=db.getValue(
                xpath + '/diffusivity/laminarAndTurbulentViscosity/laminarViscosityCoefficient'),
            turbulentViscosityCoefficient=db.getValue(
                xpath + '/diffusivity/laminarAndTurbulentViscosity/turbulentViscosityCoefficient'))

    @classmethod
    def addUserDefinedScalar(cls, db, scalar):
        newID = db.availableID(USER_DEFINED_SCALAR_XPATH, 'scalarID')

        scalars = _rootElement()
        scalars.append(
            xml.createElement(
                f'<scalar scalarID="{newID}" xmlns="http://www.baramcfd.org/baram">'
                f'  <fieldName>{scalar.fieldName}</fieldName>'
                f'  <region>{scalar.rname}</region>'
                f'  <material>{scalar.material}</material>'
                '   <diffusivity>'
                f'      <specificationMethod>{scalar.specificationMethod.value}</specificationMethod>'
                f'      <constant>{scalar.constantDiffusivity}</constant>'
                '       <laminarAndTurbulentViscosity>'
                f'          <laminarViscosityCoefficient>{scalar.laminarViscosityCoefficient}</laminarViscosityCoefficient>'
                f'          <turbulentViscosityCoefficient>{scalar.turbulentViscosityCoefficient}</turbulentViscosityCoefficient>'
                '       </laminarAndTurbulentViscosity>'
                '  </diffusivity>'
                '</scalar>'))

        for observer in cls._observers:
            observer.scalarAdded(db, newID)

        db.increaseConfigCount()

    @classmethod
    def removeUserDefinedScalar(cls, db, scalarID):
        scalars = _rootElement()

        scalar = xml.getElement(scalars, f'scalar[@scalarID="{scalarID}"]')
        if scalar is None:
            raise LookupError

        for observer in cls._observers:
            observer.scalarRemoving(db, scalarID)

        scalars.remove(scalar)

        db.increaseConfigCount()

    @classmethod
    def clearUserDefinedScalars(cls, db):
        removed = False

        scalars = _rootElement()
        for scalar in xml.getElements(scalars, 'scalar'):
            if xml.getAttribute(scalar, 'scalarID') != '0':
                scalars.remove(scalar)
                removed = True

        if removed:
            db.increaseConfigCount()

    @classmethod
    def isReferenced(cls, scalarID):
        return int(scalarID) and coredb.CoreDB().exists(f'monitors/*/*/field[field="scalar"][fieldID="{scalarID}"]')


class MaterialObserver(IMaterialObserver):
    def materialRemoving(self, db, mid: str):
        scalars = [xml.getText(e, 'fieldName') for e in db.getElements(f'{USER_DEFINED_SCALAR_XPATH}[material="{mid}"]')]
        if scalars:
            raise ConfigurationException(
                self.tr('{} is referenced by user-defined scalars {}').format(
                    MaterialDB.getName(mid), ' '.join(scalars)))
