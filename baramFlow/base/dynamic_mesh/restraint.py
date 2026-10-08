#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from enum import Enum
from uuid import UUID, uuid4

from baramFlow.coredb.libdb import E, nsmap
from baramFlow.base.base import Vector
from libbaram.pfloat import PFloat


class RestraintType(Enum):
    SIMPLE_DAMPER         = 'simpleDamper'
    TRANSLATIONAL_SPRING  = 'translationalSpring'
    ROTATIONAL_SPRING     = 'rotationalSpring'


@dataclass(kw_only=True)
class Restraint:
    uuid: UUID = dataClassField(default_factory=uuid4)
    order: int
    restraintType: RestraintType

    dampingConstant: PFloat = dataClassField(default_factory=lambda: PFloat('0'))
    springConstant: PFloat = dataClassField(default_factory=lambda: PFloat('0'))
    restLength: PFloat = dataClassField(default_factory=lambda: PFloat('0'))

    axis: Vector = dataClassField(default_factory=Vector.zUnit)
    attachmentPoint: Vector = dataClassField(default_factory=Vector.zero)
    anchorPoint: Vector = dataClassField(default_factory=Vector.zero)

    useBoundaryOrientation: bool = True
    orientation: list[PFloat] = dataClassField(default_factory=lambda: [PFloat('1'), PFloat('0'), PFloat('0'),
                                                                        PFloat('0'), PFloat('1'), PFloat('0'),
                                                                        PFloat('0'), PFloat('0'), PFloat('1')])

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        order = int(e.find('order', namespaces=nsmap).text)
        restraintType = RestraintType(e.find('restraintType', namespaces=nsmap).text)

        dampingConstant = PFloat.fromElement(e.find('dampingConstant', namespaces=nsmap))
        springConstant = PFloat.fromElement(e.find('springConstant', namespaces=nsmap))
        restLength = PFloat.fromElement(e.find('restLength', namespaces=nsmap))

        axis = Vector.fromElement(e.find('axis', namespaces=nsmap))
        attachmentPoint = Vector.fromElement(e.find('attachmentPoint', namespaces=nsmap))
        anchorPoint = Vector.fromElement(e.find('anchorPoint', namespaces=nsmap))

        useBoundaryOrientation = e.find('useBoundaryOrientation', namespaces=nsmap).text == 'true'

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

        return Restraint(uuid=uuid, order=order, restraintType=restraintType,
                         dampingConstant=dampingConstant,
                         springConstant=springConstant,
                         restLength=restLength,
                         axis=axis,
                         attachmentPoint=attachmentPoint,
                         anchorPoint=anchorPoint,
                         useBoundaryOrientation=useBoundaryOrientation,
                         orientation=orientation)

    def toElement(self, tag):
        return E(tag,
                 E('uuid', str(self.uuid)),
                 E('order', str(self.order)),
                 E('restraintType', self.restraintType.value),
                 self.dampingConstant.toElement('dampingConstant'),
                 self.springConstant.toElement('springConstant'),
                 self.restLength.toElement('restLength'),
                 self.axis.toElement('axis'),
                 self.attachmentPoint.toElement('attachmentPoint'),
                 self.anchorPoint.toElement('anchorPoint'),
                 E('useBoundaryOrientation', self.useBoundaryOrientation),
                 E('orientation',
                    self.orientation[0].toElement('r11'),
                    self.orientation[1].toElement('r12'),
                    self.orientation[2].toElement('r13'),
                    self.orientation[3].toElement('r21'),
                    self.orientation[4].toElement('r22'),
                    self.orientation[5].toElement('r23'),
                    self.orientation[6].toElement('r31'),
                    self.orientation[7].toElement('r32'),
                    self.orientation[8].toElement('r33')))
