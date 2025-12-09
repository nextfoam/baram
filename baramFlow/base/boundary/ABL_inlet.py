#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from baramFlow.base.boundary.boundary import UserDefinedScalarValue, SpecieValue, BoundaryManager, BoundaryTypeCondition
from baramFlow.base.xml_helper import Vector
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import FlowDirectionSpecificationMethod
from baramFlow.coredb.general_db import GeneralDB


@dataclass
class ABLFlowDirection:
    specificationMethod: FlowDirectionSpecificationMethod
    value: Vector = None


@dataclass
class PasquillStability:
    disabled: bool
    stabilityClass: str = None
    latitude: str = None
    surfaceHeatFlux: str = None
    referenceDensity: str = None
    referenceSpecificHeat: str = None
    referenceTemperature: str = None


@dataclass
class AtmosphericBoundaryLayer:
    flowDirection: ABLFlowDirection
    groundNormalDirection: Vector
    referenceFlowSpeed: str
    referenceHeight: str
    surfaceRoughnessLength: str
    minimumZCoordinate: str
    pasquillStability: PasquillStability


@dataclass
class ABLInletCondition(BoundaryTypeCondition):
    abl: AtmosphericBoundaryLayer
    userDefinedScalars: list[UserDefinedScalarValue]
    species: list[SpecieValue]


def updateABLInletBoundaryConditions(bcid, conditions: ABLInletCondition):
    xpath = GeneralDB.GENERAL_XPATH + '/atmosphericBoundaryLayer'
    with coredb.CoreDB() as db:
        abl = conditions.abl

        db.setValue(xpath + '/flowDirection/specMethod', abl.flowDirection.specificationMethod.value)
        if abl.flowDirection.specificationMethod == FlowDirectionSpecificationMethod.DIRECT:
            db.setValue(xpath + '/flowDirection/value/x', abl.flowDirection.value.x)
            db.setValue(xpath + '/flowDirection/value/y', abl.flowDirection.value.y)
            db.setValue(xpath + '/flowDirection/value/z', abl.flowDirection.value.z)

        db.setValue(xpath + '/groundNormalDirection/x', abl.groundNormalDirection.x)
        db.setValue(xpath + '/groundNormalDirection/y', abl.groundNormalDirection.y)
        db.setValue(xpath + '/groundNormalDirection/z', abl.groundNormalDirection.z)

        db.setValue(xpath + '/referenceFlowSpeed', abl.referenceFlowSpeed)
        db.setValue(xpath + '/referenceHeight', abl.referenceHeight)
        db.setValue(xpath + '/surfaceRoughnessLength', abl.surfaceRoughnessLength)
        db.setValue(xpath + '/minimumZCoordinate', abl.minimumZCoordinate)

        pasquillStability = abl.pasquillStability
        if pasquillStability.disabled:
            db.setAttribute(xpath + '/pasquillStability', 'disabled', 'true')
        else:
            db.setAttribute(xpath + '/pasquillStability', 'disabled', 'false')
            db.setValue(xpath + '/pasquillStability/stabilityClass', pasquillStability.stabilityClass)
            db.setValue(xpath + '/pasquillStability/latitude', pasquillStability.latitude)
            db.setValue(xpath + '/pasquillStability/surfaceHeatFlux', pasquillStability.surfaceHeatFlux)
            db.setValue(xpath + '/pasquillStability/referenceDensity', pasquillStability.referenceDensity)
            db.setValue(xpath + '/pasquillStability/referenceSpecificHeat', pasquillStability.referenceSpecificHeat)
            db.setValue(xpath + '/pasquillStability/referenceTemperature', pasquillStability.referenceTemperature)

        BoundaryManager.updateUserDefinedScalars(db, bcid, conditions.userDefinedScalars)
        BoundaryManager.updateSpecies(db, bcid, conditions.species)

        db.increaseConfigCount()
