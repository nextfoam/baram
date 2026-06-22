#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from enum import Enum
from uuid import UUID, uuid4

from bidict import bidict

from baramFlow.coredb.libdb import E, nsmap
from baramFlow.base.base import Vector
from baramFlow.base.dynamic_mesh.rigid_body_solver import RigidBodySolver
from baramFlow.base.dynamic_mesh.restraint import Restraint
from libbaram.pfloat import PFloat


class JointType(Enum):
    PRISMATIC  = 'prismatic'
    REVOLUTE   = 'revolute'
    SPHERICAL  = 'spherical'


@dataclass
class Joint:
    jointType: JointType

    direction: Vector = dataClassField(default_factory=Vector.xUnit)
    axis: Vector = dataClassField(default_factory=Vector.zUnit)

    @classmethod
    def fromElement(cls, e):
        jointType = JointType(e.find('jointType', namespaces=nsmap).text)
        direction = Vector.fromElement(e.find('direction', namespaces=nsmap))
        axis = Vector.fromElement(e.find('axis', namespaces=nsmap))

        return Joint(jointType=jointType, direction=direction, axis=axis)

    def toElement(self, tag):
        return E(tag,
                 E('jointType', self.jointType.value),
                 self.direction.toElement('direction'),
                 self.axis.toElement('axis'))


@dataclass(kw_only=True)
class Body:
    uuid: UUID = dataClassField(default_factory=uuid4)
    name: str
    parent: UUID

    mass: PFloat = dataClassField(default_factory=lambda: PFloat('0'))

    centerOfMass: Vector = dataClassField(default_factory=Vector.zero)
    localOrigin: Vector = dataClassField(default_factory=Vector.zero)

    orientation: list[PFloat] = dataClassField(default_factory=lambda: [PFloat('1'), PFloat('0'), PFloat('0'),
                                                                        PFloat('0'), PFloat('1'), PFloat('0'),
                                                                        PFloat('0'), PFloat('0'), PFloat('1')])
    momentOfInertia: list[PFloat] = dataClassField(default_factory=lambda: [PFloat('1'), PFloat('0'), PFloat('0'),
                                                                        PFloat('1'), PFloat('0'), PFloat('1')])

    boundaries: list[str] = dataClassField(default_factory=list)
    joints: list[Joint] = dataClassField(default_factory=list)
    restraints: list[Restraint] = dataClassField(default_factory=list)

    deformationOffset: PFloat = dataClassField(default_factory=lambda: PFloat('0'))
    deformationDistance: PFloat = dataClassField(default_factory=lambda: PFloat('0'))

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text
        parent = UUID(e.find('parent', namespaces=nsmap).text)

        mass = PFloat.fromElement(e.find('mass', namespaces=nsmap))

        centerOfMass = Vector.fromElement(e.find('centerOfMass', namespaces=nsmap))
        localOrigin = Vector.fromElement(e.find('localOrigin', namespaces=nsmap))

        oe = e.find('orientation', namespaces=nsmap)
        orientation =  [PFloat.fromElement(oe.find('r11', namespaces=nsmap)),
                        PFloat.fromElement(oe.find('r12', namespaces=nsmap)),
                        PFloat.fromElement(oe.find('r13', namespaces=nsmap)),
                        PFloat.fromElement(oe.find('r21', namespaces=nsmap)),
                        PFloat.fromElement(oe.find('r22', namespaces=nsmap)),
                        PFloat.fromElement(oe.find('r23', namespaces=nsmap)),
                        PFloat.fromElement(oe.find('r31', namespaces=nsmap)),
                        PFloat.fromElement(oe.find('r32', namespaces=nsmap)),
                        PFloat.fromElement(oe.find('r33', namespaces=nsmap))]

        me = e.find('momentOfInertia', namespaces=nsmap)
        momentOfInertia = [PFloat.fromElement(me.find('ixx', namespaces=nsmap)),
                           PFloat.fromElement(me.find('ixy', namespaces=nsmap)),
                           PFloat.fromElement(me.find('ixz', namespaces=nsmap)),
                           PFloat.fromElement(me.find('iyy', namespaces=nsmap)),
                           PFloat.fromElement(me.find('iyz', namespaces=nsmap)),
                           PFloat.fromElement(me.find('izz', namespaces=nsmap))]

        boundariesText = e.find('boundaries', namespaces=nsmap).text or ''
        boundaries: list[str] = boundariesText.split() if boundariesText.strip() else []

        joints = []
        jointsElement = e.find('joints', namespaces=nsmap)
        for je in jointsElement.findall('joint', namespaces=nsmap):
            joints.append(Joint.fromElement(je))

        restraints = []
        for re_ in e.find('rigidBodyRestraints', namespaces=nsmap).findall('restraint', namespaces=nsmap):
            restraints.append(Restraint.fromElement(re_))
        restraints.sort(key=lambda r: r.order)

        deformationOffset = PFloat.fromElement(e.find('deformationOffset', namespaces=nsmap))
        deformationDistance = PFloat.fromElement(e.find('deformationDistance', namespaces=nsmap))

        return Body(uuid=uuid, name=name, parent=parent,
                    mass=mass,
                    centerOfMass=centerOfMass,
                    localOrigin=localOrigin,
                    orientation=orientation,
                    momentOfInertia=momentOfInertia,
                    boundaries=boundaries,
                    joints=joints,
                    restraints=restraints,
                    deformationOffset=deformationOffset,
                    deformationDistance=deformationDistance)

    def toElement(self, tag):
        return E(tag,
                 E('uuid', str(self.uuid)),
                 E('name', self.name),
                 E('parent', str(self.parent)),
                 self.mass.toElement('mass'),
                 self.centerOfMass.toElement('centerOfMass'),
                 self.localOrigin.toElement('localOrigin'),
                 E('orientation',
                    self.orientation[0].toElement('r11'),
                    self.orientation[1].toElement('r12'),
                    self.orientation[2].toElement('r13'),
                    self.orientation[3].toElement('r21'),
                    self.orientation[4].toElement('r22'),
                    self.orientation[5].toElement('r23'),
                    self.orientation[6].toElement('r31'),
                    self.orientation[7].toElement('r32'),
                    self.orientation[8].toElement('r33')),
                 E('momentOfInertia',
                    self.momentOfInertia[0].toElement('ixx'),
                    self.momentOfInertia[1].toElement('ixy'),
                    self.momentOfInertia[2].toElement('ixz'),
                    self.momentOfInertia[3].toElement('iyy'),
                    self.momentOfInertia[4].toElement('iyz'),
                    self.momentOfInertia[5].toElement('izz')),
                 E('boundaries', ' '.join(self.boundaries)),
                 E('joints', *[j.toElement('joint') for j in self.joints]),
                 E('rigidBodyRestraints', *[r.toElement('restraint') for r in self.restraints]),
                 self.deformationOffset.toElement('deformationOffset'),
                 self.deformationDistance.toElement('deformationDistance'))

    def processMeshUpdate(self, oldBoundaries: bidict[str, str], newBoundaries: bidict[str, str]):
        boundaries: list[str] = []
        for boundary in self.boundaries:
            name = oldBoundaries.inverse[boundary]
            if name in newBoundaries:
                boundaries.append(newBoundaries[name])

        self.boundaries = boundaries


@dataclass
class RigidBodyDynamics:
    solver: RigidBodySolver = dataClassField(default_factory=RigidBodySolver)
    accelerationRelaxationFactor: PFloat = dataClassField(default_factory=lambda: PFloat('0.7'))
    accelerationDampingFactor: PFloat = dataClassField(default_factory=lambda: PFloat('1.0'))
    bodies: list[Body] = dataClassField(default_factory=list)

    @classmethod
    def fromElement(cls, e):
        solver = RigidBodySolver.fromElement(e.find('rigidBodySolverType', namespaces=nsmap))
        accelerationRelaxationFactor = PFloat.fromElement(e.find('accelerationRelaxationFactor', namespaces=nsmap))
        accelerationDampingFactor = PFloat.fromElement(e.find('accelerationDampingFactor', namespaces=nsmap))

        bodies = []
        bodiesElement = e.find('bodies', namespaces=nsmap)
        for be in bodiesElement.findall('body', namespaces=nsmap):
            bodies.append(Body.fromElement(be))

        return RigidBodyDynamics(
            solver=solver,
            accelerationRelaxationFactor=accelerationRelaxationFactor,
            accelerationDampingFactor=accelerationDampingFactor,
            bodies=bodies)

    def toElement(self):
        bodiesElement = E('bodies')
        for b in self.bodies:
            bodiesElement.append(b.toElement('body'))

        return E('rigidBodyDynamics',
                 self.solver.toElement(),
                 self.accelerationRelaxationFactor.toElement('accelerationRelaxationFactor'),
                 self.accelerationDampingFactor.toElement('accelerationDampingFactor'),
                 bodiesElement)
