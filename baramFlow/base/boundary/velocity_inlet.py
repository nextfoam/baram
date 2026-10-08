#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField

from enum import Enum

from baramFlow.base.base import SimpleSheetData
from baramFlow.base.base import SpatialVectorList, TemporalScalarList, TemporalVectorList
from baramFlow.base.base import Vector
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import E


class VelocitySpecification(Enum):
    COMPONENT = 'component'
    MAGNITUDE = 'magnitudeNormal'


class VelocityProfile(Enum):
    CONSTANT = 'constant'
    SPATIAL_DISTRIBUTION = 'spatialDistribution'
    TEMPORAL_DISTRIBUTION = 'temporalDistribution'


class CoordinateSystem(Enum):
    CARTESIAN = 'cartesian'
    LOCAL_CYLINDRICAL = 'localCylindrical'


@dataclass
class CartesianTemporalDistribution:
    piecewiseLinear: TemporalVectorList = dataClassField(default_factory=TemporalVectorList.default)

    def toElement(self):
        return E('temporalDistribution',
                    E('specification', 'piecewiseLinear'),
                    self.piecewiseLinear.toElement('piecewiseLinear'))


@dataclass
class VelocityComponentCartesian:
    profile: VelocityProfile                                = VelocityProfile.CONSTANT
    constant: Vector                                        = dataClassField(default_factory=Vector.xUnit)
    spatialDistribution: SpatialVectorList                  = dataClassField(default_factory=SpatialVectorList.default)
    temporalDistribution: CartesianTemporalDistribution     = dataClassField(default_factory=CartesianTemporalDistribution)

    def toElement(self):
        return E('component',
                    E('profile', self.profile),
                    self.constant.toElement('constant'),
                    self.spatialDistribution.toElement('spatialDistribution'),
                    self.temporalDistribution.toElement())


@dataclass
class MagnitudeTemporalDistribution:
    piecewiseLinear: TemporalScalarList = dataClassField(default_factory=TemporalScalarList.default)

    def toElement(self):
        return E('temporalDistribution',
                 E('specification', 'piecewiseLinear'),
                 self.piecewiseLinear.toElement('piecewiseLinear'))


@dataclass
class VelocityMagnitude:
    profile: VelocityProfile                            = VelocityProfile.CONSTANT
    constant: str                                       = '1'
    temporalDistribution: MagnitudeTemporalDistribution = dataClassField(default_factory=MagnitudeTemporalDistribution)

    def toElement(self):
        return E('magnitudeNormal',
                    E('profile', self.profile),
                    E('constant', self.constant),
                    self.temporalDistribution.toElement())


@dataclass
class LocalCylindricalConstant:
    axialVelocity: str  = '0'
    radialVelocity: str = '0'
    angularSpeed: str   = '0'

    def toElement(self):
        return E('constant',
                    E('axialVelocity', self.axialVelocity),
                    E('radialVelocity', self.radialVelocity),
                    E('angularSpeed', self.angularSpeed))


class LocalCylindricalTemporalDistribution(SimpleSheetData):
    columns = ['t', 'u', 'v', 'omega']


@dataclass
class VelocityLocalCylindrical:
    profile: VelocityProfile                                    = VelocityProfile.CONSTANT
    constant: LocalCylindricalConstant                          = dataClassField(default_factory=LocalCylindricalConstant)
    temporalDistribution: LocalCylindricalTemporalDistribution  = dataClassField(default_factory=LocalCylindricalTemporalDistribution.default)
    axisOrigin: Vector                                          = dataClassField(default_factory=Vector.zero)
    axisDirection: Vector                                       = dataClassField(default_factory=Vector.zUnit)

    def toElement(self):
        return E('localCylindrical',
                    E('profile', self.profile),
                    self.constant.toElement(),
                    self.temporalDistribution.toElement('temporalDistribution'),
                    self.axisOrigin.toElement('axisOrigin'),
                    self.axisDirection.toElement('axisDirection'))


@dataclass
class InletVelocity:
    specificationMethod: VelocitySpecification  = VelocitySpecification.MAGNITUDE
    coordinateSystem: CoordinateSystem          = CoordinateSystem.CARTESIAN
    component: VelocityComponentCartesian       = dataClassField(default_factory=VelocityComponentCartesian)
    magnitude: VelocityMagnitude                = dataClassField(default_factory=VelocityMagnitude)
    localCylindrical: VelocityLocalCylindrical  = dataClassField(default_factory=VelocityLocalCylindrical)

    def applyToDB(self, db, bcid):
        xpath = BoundaryDB.getXPath(bcid) + '/velocityInlet/velocity'

        db.setValue(xpath + '/specification', self.specificationMethod.value)
        db.setValue(xpath + '/coordinateSystem', self.coordinateSystem.value)

        if self.specificationMethod == VelocitySpecification.MAGNITUDE:
            db.setValue(xpath + '/magnitudeNormal/profile', self.magnitude.profile.value)
            if self.magnitude.profile == VelocityProfile.CONSTANT:
                db.setValue(xpath + '/magnitudeNormal/constant', self.magnitude.constant)
            elif self.magnitude.profile == VelocityProfile.TEMPORAL_DISTRIBUTION:
                if self.magnitude.temporalDistribution.piecewiseLinear is not None:
                    db.replaceElement(xpath + '/magnitudeNormal/temporalDistribution/piecewiseLinear',
                                      self.magnitude.temporalDistribution.piecewiseLinear.toElement('piecewiseLinear'))
        elif self.coordinateSystem == CoordinateSystem.CARTESIAN:
            db.setValue(xpath + '/component/profile', self.component.profile.value)
            if self.component.profile == VelocityProfile.CONSTANT:
                db.replaceElement(xpath + '/component/constant', self.component.constant.toElement('constant'))
            elif self.component.profile == VelocityProfile.SPATIAL_DISTRIBUTION:
                if self.component.spatialDistribution is not None:
                    db.replaceElement(xpath + '/component/spatialDistribution',
                                      self.component.spatialDistribution.toElement('spatialDistribution'))
            elif self.component.profile == VelocityProfile.TEMPORAL_DISTRIBUTION:
                if self.component.temporalDistribution.piecewiseLinear is not None:
                    db.replaceElement(xpath + '/component/temporalDistribution/piecewiseLinear',
                                      self.component.temporalDistribution.piecewiseLinear.toElement('piecewiseLinear'))
        else:
            db.setValue(xpath + '/localCylindrical/profile', self.localCylindrical.profile.value)
            if self.localCylindrical.profile == VelocityProfile.CONSTANT:
                db.setValue(xpath + '/localCylindrical/constant/axialVelocity',
                            self.localCylindrical.constant.axialVelocity)
                db.setValue(xpath + '/localCylindrical/constant/radialVelocity',
                            self.localCylindrical.constant.radialVelocity)
                db.setValue(xpath + '/localCylindrical/constant/angularSpeed',
                            self.localCylindrical.constant.angularSpeed)
            elif self.localCylindrical.profile == VelocityProfile.TEMPORAL_DISTRIBUTION:
                if self.localCylindrical.temporalDistribution is not None:
                    db.replaceElement(xpath + '/localCylindrical/temporalDistribution',
                                      self.localCylindrical.temporalDistribution.toElement('temporalDistribution'))

            db.replaceElement(xpath + '/localCylindrical/axisOrigin',
                              self.localCylindrical.axisOrigin.toElement('axisOrigin'))
            db.replaceElement(xpath + '/localCylindrical/axisDirection',
                              self.localCylindrical.axisDirection.toElement('axisDirection'))

    def toElement(self):
        return E('velocity',
                    E('specification', self.specificationMethod),
                    E('coordinateSystem', self.coordinateSystem),
                    self.component.toElement(),
                    self.magnitude.toElement(),
                    self.localCylindrical.toElement())


@dataclass
class VelocityInlet:
    velocity: InletVelocity = dataClassField(default_factory=InletVelocity)

    def applyToDB(self, db, bcid):
        self.velocity.applyToDB(db, bcid)

    def toElement(self):
        return self.velocity.toElement()
