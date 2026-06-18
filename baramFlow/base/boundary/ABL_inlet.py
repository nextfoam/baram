#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from baramFlow.base.xml_helper import Vector
from baramFlow.coredb.boundary_db import FlowDirectionSpecificationMethod
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.libdb import E
from libbaram.pfloat import PFloat


@dataclass
class ABLFlowDirection:
    specificationMethod: FlowDirectionSpecificationMethod
    value: Vector = None


@dataclass
class PasquillStability:
    disabled: bool
    stabilityClass: str             = None
    latitude: PFloat                = None
    surfaceHeatFlux: PFloat         = None
    referenceDensity: PFloat        = None
    referenceSpecificHeat: PFloat   = None
    referenceTemperature: PFloat    = None

    def toElement(self):
        if self.disabled:
            return None

        return E('pasquillStability',
                 E('stabilityClass',        self.stabilityClass),
                 self.latitude.toElement('latitude'),
                 self.surfaceHeatFlux.toElement('surfaceHeatFlux'),
                 self.referenceDensity.toElement('referenceDensity'),
                 self.referenceSpecificHeat.toElement('referenceSpecificHeat'),
                 self.referenceTemperature.toElement('referenceTemperature'),
                 disabled=self.disabled)


@dataclass
class AtmosphericBoundaryLayer:
    flowDirection: ABLFlowDirection
    groundNormalDirection: Vector
    referenceFlowSpeed: str
    referenceHeight: str
    surfaceRoughnessLength: str
    minimumZCoordinate: str
    pasquillStability: PasquillStability

    def applyToDB(self, db):
        xpath = GeneralDB.GENERAL_XPATH + '/atmosphericBoundaryLayer'

        db.setValue(xpath + '/flowDirection/specMethod', self.flowDirection.specificationMethod.value)
        if self.flowDirection.specificationMethod == FlowDirectionSpecificationMethod.DIRECT:
            db.replaceElement(xpath + '/flowDirection/value', self.flowDirection.value.toElement('value'))

        db.replaceElement(xpath + '/groundNormalDirection',
                          self.groundNormalDirection.toElement('groundNormalDirection'))
        db.setValue(xpath + '/referenceFlowSpeed', self.referenceFlowSpeed)
        db.setValue(xpath + '/referenceHeight', self.referenceHeight)
        db.setValue(xpath + '/surfaceRoughnessLength', self.surfaceRoughnessLength)
        db.setValue(xpath + '/minimumZCoordinate', self.minimumZCoordinate)

        if self.pasquillStability.disabled:
            db.setAttribute(xpath + '/pasquillStability', 'disabled', 'true')
        else:
            db.replaceElement(xpath + '/pasquillStability', self.pasquillStability.toElement())

        db.increaseConfigCount()

