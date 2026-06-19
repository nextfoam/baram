#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from libbaram.pfloat import PFloat

from baramFlow.base.base import DirectionSpecificationMethod
from baramFlow.base.base import Vector
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.coredb import _CoreDB
from baramFlow.coredb.libdb import nsmap


@dataclass
class FlowDirection:
    specificationMethod: DirectionSpecificationMethod
    flowDirection: Vector   = None
    dragDirection: Vector   = None
    liftDirection: Vector   = None
    angleOfAttack: PFloat   = field(default_factory=lambda: PFloat('0'))
    angleOfSideslip: PFloat = field(default_factory=lambda: PFloat('0'))

    def applyToDBByPath(self, db: _CoreDB, parentPath: str):
        element = db.getElement(parentPath + '/flowDirection')
        element.find('specificationMethod', namespaces=nsmap).text = self.specificationMethod.value
        if self.specificationMethod == DirectionSpecificationMethod.DIRECT:
            element.replace(element.find('flowDirection', namespaces=nsmap),
                            self.flowDirection.toElement('flowDirection'))
        elif self.specificationMethod == DirectionSpecificationMethod.AOA_AOS:
            element.replace(element.find('dragDirection', namespaces=nsmap),
                            self.dragDirection.toElement('dragDirection'))
            element.replace(element.find('liftDirection', namespaces=nsmap),
                            self.liftDirection.toElement('liftDirection'))
            element.replace(element.find('angleOfAttack', namespaces=nsmap),
                            self.angleOfAttack.toElement('angleOfAttack'))
            element.replace(element.find('angleOfSideslip', namespaces=nsmap),
                            self.angleOfSideslip.toElement('angleOfSideslip'))


@dataclass
class FreeStream:
    flowDirection: FlowDirection
    speed: str
    pressure: str

    def applyToDB(self, db: _CoreDB, bcid: str):
        xpath = BoundaryDB.getXPath(bcid) + '/freeStream'
        self.flowDirection.applyToDBByPath(db, xpath)
        db.setValue(xpath + '/speed', self.speed)
        db.setValue(xpath + '/pressure', self.pressure)


@dataclass
class FarFieldRiemann:
    flowDirection: FlowDirection
    machNumber: str
    staticPressure: str
    staticTemperature: str

    def applyToDB(self, db: _CoreDB, bcid: str):
        xpath = BoundaryDB.getXPath(bcid) + '/farFieldRiemann'
        self.flowDirection.applyToDBByPath(db, xpath)
        db.setValue(xpath + '/machNumber', self.machNumber)
        db.setValue(xpath + '/staticPressure', self.staticPressure)
        db.setValue(xpath + '/staticTemperature', self.staticTemperature)
