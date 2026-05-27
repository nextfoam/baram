#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from enum import Enum
from uuid import UUID, uuid4

from libbaram.pfloat import PFloat

from baramFlow.coredb.libdb import E, nsmap
from baramFlow.base.base import Vector


class MotionFunctionType(Enum):
    ROTATION              = 'rotation'
    ROTATING_OSCILLATION  = 'rotatingOscillation'
    LINEAR_TRANSLATION    = 'linearTranslation'
    LINEAR_OSCILLATION    = 'linearOscillation'
    MANUAL_POSITION       = 'manualPosition'


@dataclass
class Positions:
    t:     list[float] = dataClassField(default_factory=list)
    surge: list[float] = dataClassField(default_factory=list)
    sway:  list[float] = dataClassField(default_factory=list)
    heave: list[float] = dataClassField(default_factory=list)
    roll:  list[float] = dataClassField(default_factory=list)
    pitch: list[float] = dataClassField(default_factory=list)
    yaw:   list[float] = dataClassField(default_factory=list)

    @classmethod
    def fromElement(cls, e):
        def parse(name):
            text = e.find(name, namespaces=nsmap).text or ''
            return [float(v) for v in text.split()]

        return Positions(t=parse('t'), surge=parse('surge'), sway=parse('sway'),
                         heave=parse('heave'), roll=parse('roll'),
                         pitch=parse('pitch'), yaw=parse('yaw'))

    def toElement(self):
        def joinFloats(values):
            return ' '.join(str(v) for v in values)

        return E('positions',
                 E('t', joinFloats(self.t)),
                 E('surge', joinFloats(self.surge)),
                 E('sway', joinFloats(self.sway)),
                 E('heave', joinFloats(self.heave)),
                 E('roll', joinFloats(self.roll)),
                 E('pitch', joinFloats(self.pitch)),
                 E('yaw', joinFloats(self.yaw)))

    @classmethod
    def fromRows(cls, rows: list[list[float]]):
        columns = [list(c) for c in zip(*rows)] if rows else [[]] * 7
        return Positions(t=columns[0], surge=columns[1], sway=columns[2], heave=columns[3],
                         roll=columns[4], pitch=columns[5], yaw=columns[6])

    def toRows(self) -> list[list[float]]:
        return [list(r) for r in zip(self.t, self.surge, self.sway, self.heave,
                                     self.roll, self.pitch, self.yaw)]


@dataclass(kw_only=True)
class MotionFunction:
    uuid: UUID = dataClassField(default_factory=uuid4)
    order: int
    functionType: MotionFunctionType

    origin: Vector = dataClassField(default_factory=Vector.zero)
    axis: Vector = dataClassField(default_factory=Vector.zUnit)
    rpm: PFloat = dataClassField(default_factory=lambda: PFloat('0'))

    velocity: Vector = dataClassField(default_factory=Vector.zero)
    angularAmplitude: Vector = dataClassField(default_factory=Vector.zero)
    linearAmplitude: Vector = dataClassField(default_factory=Vector.zero)

    frequency: PFloat = dataClassField(default_factory=lambda: PFloat('0'))

    positions: Positions = None

    def __post_init__(self):
        if self.positions is None:
            self.positions = Positions()

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        order = int(e.find('order', namespaces=nsmap).text)
        functionType = MotionFunctionType(e.find('functionType', namespaces=nsmap).text)

        origin = Vector.fromElement(e.find('origin', namespaces=nsmap))
        axis = Vector.fromElement(e.find('axis', namespaces=nsmap))
        rpm = PFloat.fromElement(e.find('rpm', namespaces=nsmap))

        velocity = Vector.fromElement(e.find('velocity', namespaces=nsmap))
        angularAmplitude = Vector.fromElement(e.find('angularAmplitude', namespaces=nsmap))
        linearAmplitude = Vector.fromElement(e.find('linearAmplitude', namespaces=nsmap))

        frequency = PFloat.fromElement(e.find('frequency', namespaces=nsmap))

        positions = Positions.fromElement(e.find('positions', namespaces=nsmap))

        return MotionFunction(uuid=uuid, order=order, functionType=functionType,
                              origin=origin,
                              axis=axis,
                              rpm=rpm,
                              velocity=velocity,
                              angularAmplitude=angularAmplitude,
                              linearAmplitude=linearAmplitude,
                              frequency=frequency,
                              positions=positions)

    def toElement(self):
        return E('motionFunction',
                 E('uuid', str(self.uuid)),
                 E('order', str(self.order)),
                 E('functionType', self.functionType.value),
                 self.origin.toElement('origin'),
                 self.axis.toElement('axis'),
                 self.rpm.toElement('rpm'),
                 self.velocity.toElement('velocity'),
                 self.angularAmplitude.toElement('angularAmplitude'),
                 self.linearAmplitude.toElement('linearAmplitude'),
                 self.frequency.toElement('frequency'),
                 self.positions.toElement())
