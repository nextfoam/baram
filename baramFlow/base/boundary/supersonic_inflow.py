#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from libbaram.pfloat import PFloat

from baramFlow.base.base import Vector
from baramFlow.coredb.libdb import E


@dataclass
class SupersonicInflow:
    velocity: Vector
    staticPressure: PFloat
    staticTemperature: PFloat

    def toElement(self):
        return E('supersonicInflow',
                 self.velocity.toElement('velocity'),
                 self.staticPressure.toElement('staticPressure'),
                 self.staticTemperature.toElement('staticTemperature'))
