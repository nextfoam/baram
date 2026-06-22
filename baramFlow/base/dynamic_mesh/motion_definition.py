#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from uuid import UUID, uuid4

from bidict import bidict

from baramFlow.coredb.libdb import E, nsmap
from baramFlow.base.dynamic_mesh.motion_function import MotionFunction


@dataclass(kw_only=True)
class MotionDefinition:
    uuid: UUID = dataClassField(default_factory=uuid4)
    name: str
    order: int
    motionFunctions: list[MotionFunction] = dataClassField(default_factory=list)
    cellZones: list[str] = dataClassField(default_factory=list)

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text
        order = int(e.find('order', namespaces=nsmap).text)

        motionFunctions = []
        for fe in e.find('motionFunctions', namespaces=nsmap).findall('motionFunction', namespaces=nsmap):
            motionFunctions.append(MotionFunction.fromElement(fe))
        motionFunctions.sort(key=lambda f: f.order)

        cellZonesText: str = e.find('cellZones', namespaces=nsmap).text
        cellZones: list[str] = cellZonesText.split() if cellZonesText else []

        return MotionDefinition(uuid=uuid, name=name, order=order,
                                motionFunctions=motionFunctions,
                                cellZones=cellZones)

    def toElement(self):
        return E('motionDefinition',
                 E('uuid', str(self.uuid)),
                 E('name', self.name),
                 E('order', str(self.order)),
                 E('motionFunctions', *[f.toElement() for f in self.motionFunctions]),
                 E('cellZones', ' '.join(self.cellZones)))

    def processMeshUpdate(self, oldCellZones: bidict[str, str], newCellZones: bidict[str, str]):
        cellZones: list[str] = []
        for czid in self.cellZones:
            name = oldCellZones.inverse[czid]
            if name in newCellZones:
                cellZones.append(newCellZones[name])

        self.cellZones = cellZones
