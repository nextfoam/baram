#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from enum import Enum
from uuid import UUID, uuid4

from libbaram.pfloat import PFloat

from baramFlow.coredb.libdb import E, nsmap
from baramFlow.base.dynamic_mesh.motion_function import MotionFunction
from baramFlow.base.dynamic_mesh.rigid_body_solver import RigidBodySolver
from baramFlow.base.dynamic_mesh.restraint import (
    Restraint,
)
from baramFlow.base.base import Vector


class PointMotionType(Enum):
    FIXED             = 'fixed'
    SLIP              = 'slip'
    PRESCRIBED_MOTION = 'prescribedMotion'
    RIGID_BODY_MOTION = 'rigidBodyMotion'
    CYCLIC            = 'cyclic'
    SYMMETRY          = 'symmetry'
    EMPTY             = 'empty'
    WEDGE             = 'wedge'


class TranslationalConstraintType(Enum):
    FREE  = 'free'
    PLANE = 'plane'
    LINE  = 'line'
    FIXED = 'fixed'


class RotationalConstraintType(Enum):
    FREE  = 'free'
    AXIS  = 'axis'
    FIXED = 'fixed'


@dataclass
class RigidBodyMotion:
    mass: PFloat = PFloat('0')

    centerOfMass: Vector = dataClassField(default_factory=Vector.zero)
    centerOfRotation: Vector = dataClassField(default_factory=Vector.zero)

    orientation: list[PFloat] = dataClassField(default_factory=lambda: [PFloat('1'), PFloat('0'), PFloat('0'),
                                                                        PFloat('0'), PFloat('1'), PFloat('0'),
                                                                        PFloat('0'), PFloat('0'), PFloat('1')])
    momentOfInertia: list[PFloat] = dataClassField(default_factory=lambda: [PFloat('1'), PFloat('1'), PFloat('1')])

    translationalConstraintType: TranslationalConstraintType = TranslationalConstraintType.FREE
    rotationalConstraintType: RotationalConstraintType = RotationalConstraintType.FREE

    direction: Vector = dataClassField(default_factory=Vector.xUnit)
    normal: Vector = dataClassField(default_factory=Vector.yUnit)
    axis: Vector = dataClassField(default_factory=Vector.zUnit)

    limitAngle: bool = False
    clockwise: PFloat = dataClassField(default_factory=lambda: PFloat('0'))
    counterclockwise: PFloat = dataClassField(default_factory=lambda: PFloat('0'))

    useBoundaryOrientation: bool = True
    constraintOrientation: list[PFloat] = dataClassField(default_factory=lambda: [PFloat('1'), PFloat('0'), PFloat('0'),
                                                                                   PFloat('0'), PFloat('1'), PFloat('0'),
                                                                                   PFloat('0'), PFloat('0'), PFloat('1')])

    restraints: list[Restraint] = dataClassField(default_factory=list)
    solver: RigidBodySolver = dataClassField(default_factory=RigidBodySolver)

    accelerationRelaxationFactor: PFloat = dataClassField(default_factory=lambda: PFloat('0.7'))
    accelerationDampingFactor: PFloat = dataClassField(default_factory=lambda: PFloat('1.0'))

    @classmethod
    def fromElement(cls, e):
        mass = PFloat.fromElement(e.find('mass', namespaces=nsmap))

        centerOfMass = Vector.fromElement(e.find('centerOfMass', namespaces=nsmap))
        centerOfRotation = Vector.fromElement(e.find('centerOfRotation', namespaces=nsmap))

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
                           PFloat.fromElement(me.find('iyy', namespaces=nsmap)),
                           PFloat.fromElement(me.find('izz', namespaces=nsmap))]

        translationalConstraintType = TranslationalConstraintType(
            e.find('translationalConstraintType', namespaces=nsmap).text)
        rotationalConstraintType = RotationalConstraintType(
            e.find('rotationalConstraintType', namespaces=nsmap).text)

        direction = Vector.fromElement(e.find('direction', namespaces=nsmap))
        normal = Vector.fromElement(e.find('normal', namespaces=nsmap))
        axis = Vector.fromElement(e.find('axis', namespaces=nsmap))

        limitAngle = e.find('limitAngle', namespaces=nsmap).text == 'true'
        clockwise = PFloat.fromElement(e.find('clockwise', namespaces=nsmap))
        counterclockwise = PFloat.fromElement(e.find('counterclockwise', namespaces=nsmap))

        useBoundaryOrientation = e.find('useBoundaryOrientation', namespaces=nsmap).text == 'true'

        coe = e.find('constraintOrientation', namespaces=nsmap)
        constraintOrientation = [PFloat.fromElement(coe.find('r11', namespaces=nsmap)),
                                 PFloat.fromElement(coe.find('r12', namespaces=nsmap)),
                                 PFloat.fromElement(coe.find('r13', namespaces=nsmap)),
                                 PFloat.fromElement(coe.find('r21', namespaces=nsmap)),
                                 PFloat.fromElement(coe.find('r22', namespaces=nsmap)),
                                 PFloat.fromElement(coe.find('r23', namespaces=nsmap)),
                                 PFloat.fromElement(coe.find('r31', namespaces=nsmap)),
                                 PFloat.fromElement(coe.find('r32', namespaces=nsmap)),
                                 PFloat.fromElement(coe.find('r33', namespaces=nsmap))]

        restraints = []
        for re_ in e.find('rigidBodyRestraints', namespaces=nsmap).findall('restraint', namespaces=nsmap):
            restraints.append(Restraint.fromElement(re_))
        restraints.sort(key=lambda r: r.order)

        solver = RigidBodySolver.fromElement(e.find('rigidBodySolverType', namespaces=nsmap))

        accelerationRelaxationFactor = PFloat.fromElement(e.find('accelerationRelaxationFactor', namespaces=nsmap))
        accelerationDampingFactor = PFloat.fromElement(e.find('accelerationDampingFactor', namespaces=nsmap))

        return RigidBodyMotion(
            mass=mass,
            centerOfMass=centerOfMass,
            centerOfRotation=centerOfRotation,
            orientation=orientation,
            momentOfInertia=momentOfInertia,
            translationalConstraintType=translationalConstraintType,
            rotationalConstraintType=rotationalConstraintType,
            direction=direction,
            normal=normal,
            axis=axis,
            limitAngle=limitAngle,
            clockwise=clockwise, counterclockwise=counterclockwise,
            useBoundaryOrientation=useBoundaryOrientation,
            constraintOrientation=constraintOrientation,
            restraints=restraints, solver=solver,
            accelerationRelaxationFactor=accelerationRelaxationFactor,
            accelerationDampingFactor=accelerationDampingFactor)

    def toElement(self):
        return E('rigidBodyMotion',
                 self.mass.toElement('mass'),
                 self.centerOfMass.toElement('centerOfMass'),
                 self.centerOfRotation.toElement('centerOfRotation'),
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
                    self.momentOfInertia[1].toElement('iyy'),
                    self.momentOfInertia[2].toElement('izz')),
                 E('translationalConstraintType', self.translationalConstraintType.value),
                 E('rotationalConstraintType', self.rotationalConstraintType.value),
                 self.direction.toElement('direction'),
                 self.normal.toElement('normal'),
                 self.axis.toElement('axis'),
                 E('limitAngle', self.limitAngle),
                 self.clockwise.toElement('clockwise'),
                 self.counterclockwise.toElement('counterclockwise'),
                 E('useBoundaryOrientation', self.useBoundaryOrientation),
                 E('constraintOrientation',
                    self.constraintOrientation[0].toElement('r11'),
                    self.constraintOrientation[1].toElement('r12'),
                    self.constraintOrientation[2].toElement('r13'),
                    self.constraintOrientation[3].toElement('r21'),
                    self.constraintOrientation[4].toElement('r22'),
                    self.constraintOrientation[5].toElement('r23'),
                    self.constraintOrientation[6].toElement('r31'),
                    self.constraintOrientation[7].toElement('r32'),
                    self.constraintOrientation[8].toElement('r33')),
                 E('rigidBodyRestraints', *[r.toElement('restraint') for r in self.restraints]),
                 self.solver.toElement(),
                 self.accelerationRelaxationFactor.toElement('accelerationRelaxationFactor'),
                 self.accelerationDampingFactor.toElement('accelerationDampingFactor'))


@dataclass(kw_only=True)
class MovingBoundaryEntry:
    uuid: UUID = dataClassField(default_factory=uuid4)
    boundary: str = '0'
    pointMotionType: PointMotionType = PointMotionType.FIXED

    useFixedNormal: bool = False
    normal: Vector = dataClassField(default_factory=Vector.yUnit)

    motionFunctions: list[MotionFunction] = dataClassField(default_factory=list)
    rigidBodyMotion: RigidBodyMotion = dataClassField(default_factory=RigidBodyMotion)

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        boundary = e.find('boundary', namespaces=nsmap).text
        pointMotionType = PointMotionType(e.find('pointMotionType', namespaces=nsmap).text)

        useFixedNormal = e.find('useFixedNormal', namespaces=nsmap).text == 'true'
        normal = Vector.fromElement(e.find('normal', namespaces=nsmap))

        motionFunctions = []
        for fe in e.find('motionFunctions', namespaces=nsmap).findall('motionFunction', namespaces=nsmap):
            motionFunctions.append(MotionFunction.fromElement(fe))
        motionFunctions.sort(key=lambda f: f.order)

        rigidBodyMotion = RigidBodyMotion.fromElement(
            e.find('rigidBodyMotion', namespaces=nsmap))

        return MovingBoundaryEntry(
            uuid=uuid, boundary=boundary, pointMotionType=pointMotionType,
            useFixedNormal=useFixedNormal,
            normal=normal,
            motionFunctions=motionFunctions,
            rigidBodyMotion=rigidBodyMotion)

    def toElement(self):
        return E('boundary',
                 E('uuid', str(self.uuid)),
                 E('boundary', self.boundary),
                 E('pointMotionType', self.pointMotionType.value),
                 E('useFixedNormal', self.useFixedNormal),
                 self.normal.toElement('normal'),
                 E('motionFunctions', *[f.toElement() for f in self.motionFunctions]),
                 self.rigidBodyMotion.toElement())
