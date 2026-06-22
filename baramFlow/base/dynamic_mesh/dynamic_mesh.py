#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from enum import Enum

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import E, nsmap
from baramFlow.base.dynamic_mesh.motion_definition import MotionDefinition
from baramFlow.base.dynamic_mesh.moving_boundary import MovingBoundaryEntry
from baramFlow.base.dynamic_mesh.rigid_body_dynamics import RigidBodyDynamics


class MotionType(Enum):
    NONE                 = 'none'
    MOVING_CELL_ZONE     = 'movingCellZone'
    MOVING_BOUNDARY      = 'movingBoundary'
    RIGID_BODY_DYNAMICS  = 'rigidBodyDynamics'


DYNAMIC_MESH_PATH = '/dynamicMesh'


@dataclass
class DynamicMesh:
    motionType: MotionType = MotionType.NONE
    motionDefinitions: list[MotionDefinition] = dataClassField(default_factory=list)
    movingBoundaries: list[MovingBoundaryEntry] = dataClassField(default_factory=list)
    rigidBodyDynamics: RigidBodyDynamics = dataClassField(default_factory=RigidBodyDynamics)

    @classmethod
    def fromElement(cls, e):
        motionType = MotionType(e.find('motionType', namespaces=nsmap).text)

        motionDefinitions = []
        movingCellZoneElement = e.find('movingCellZone', namespaces=nsmap)
        for mde in movingCellZoneElement.findall('motionDefinition', namespaces=nsmap):
            motionDefinitions.append(MotionDefinition.fromElement(mde))
        motionDefinitions.sort(key=lambda md: md.order)

        movingBoundaries = []
        movingBoundaryElement = e.find('movingBoundary', namespaces=nsmap)
        for be in movingBoundaryElement.findall('boundary', namespaces=nsmap):
            movingBoundaries.append(MovingBoundaryEntry.fromElement(be))

        rigidBodyDynamics = RigidBodyDynamics.fromElement(
            e.find('rigidBodyDynamics', namespaces=nsmap))

        return DynamicMesh(motionType=motionType,
                           motionDefinitions=motionDefinitions,
                           movingBoundaries=movingBoundaries,
                           rigidBodyDynamics=rigidBodyDynamics)

    def replaceWith(self, other: 'DynamicMesh'):
        self.motionType = other.motionType
        self.motionDefinitions = other.motionDefinitions
        self.movingBoundaries = other.movingBoundaries
        self.rigidBodyDynamics = other.rigidBodyDynamics

    def toElement(self, tag):
        movingCellZoneElement = E('movingCellZone')
        for md in self.motionDefinitions:
            movingCellZoneElement.append(md.toElement())

        movingBoundaryElement = E('movingBoundary')
        for mb in self.movingBoundaries:
            movingBoundaryElement.append(mb.toElement())

        return E(tag,
                 E('motionType', self.motionType.value),
                 movingCellZoneElement,
                 movingBoundaryElement,
                 self.rigidBodyDynamics.toElement())
