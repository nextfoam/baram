#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from libbaram.pfloat import PFloat

from baramFlow.base.base import Vector
from baramFlow.coredb.boundary_db import FlowDirectionSpecificationMethod
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.libdb import E


@dataclass
class ABLFlowDirection:
    specificationMethod: FlowDirectionSpecificationMethod
    value: Vector = None


@dataclass
class PasquillStability:
    disabled: bool
    stabilityClass: str             = None
    latitude: PFloat                = field(default_factory=lambda: PFloat('37'))
    surfaceHeatFlux: PFloat         = field(default_factory=lambda: PFloat('0'))
    referenceDensity: PFloat        = field(default_factory=lambda: PFloat('1.225'))
    referenceSpecificHeat: PFloat   = field(default_factory=lambda: PFloat('1006.0'))
    referenceTemperature: PFloat    = field(default_factory=lambda: PFloat('298.15'))

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
    referenceFlowSpeed: PFloat
    referenceHeight: PFloat
    surfaceRoughnessLength: PFloat
    minimumZCoordinate: PFloat
    pasquillStability: PasquillStability

    def applyToDB(self, db):
        xpath = GeneralDB.GENERAL_XPATH + '/atmosphericBoundaryLayer'

        db.setValue(xpath + '/flowDirection/specMethod', self.flowDirection.specificationMethod.value)
        if self.flowDirection.specificationMethod == FlowDirectionSpecificationMethod.DIRECT:
            db.replaceElement(xpath + '/flowDirection/value', self.flowDirection.value.toElement('value'))

        db.replaceElement(xpath + '/groundNormalDirection',
                          self.groundNormalDirection.toElement('groundNormalDirection'))
        db.setValue(xpath + '/referenceFlowSpeed', str(self.referenceFlowSpeed))
        db.setValue(xpath + '/referenceHeight', str(self.referenceHeight))
        db.setValue(xpath + '/surfaceRoughnessLength', str(self.surfaceRoughnessLength))
        db.setValue(xpath + '/minimumZCoordinate', str(self.minimumZCoordinate))

        if self.pasquillStability.disabled:
            db.setAttribute(xpath + '/pasquillStability', 'disabled', 'true')
        else:
            db.replaceElement(xpath + '/pasquillStability', self.pasquillStability.toElement())

        db.increaseConfigCount()

