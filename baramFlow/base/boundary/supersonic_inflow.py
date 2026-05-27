#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from baramFlow.base.base import Vector
from baramFlow.coredb.libdb import E


@dataclass
class SupersonicInflow:
    velocity: Vector
    staticPressure: str
    staticTemperature: str

    def toElement(self):
        return E('supersonicInflow',
                 self.velocity.toElement('velocity'),
                 E('staticPressure',    self.staticPressure),
                 E('staticTemperature', self.staticTemperature))
