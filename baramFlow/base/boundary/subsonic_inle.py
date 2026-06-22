#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from libbaram.pfloat import PFloat

from baramFlow.base.base import Vector
from baramFlow.coredb.libdb import E


@dataclass
class SubsonicInlet:
    flowDirection: Vector
    totalPressure: PFloat
    totalTemperature: PFloat

    def toElement(self):
        return E('subsonicInlet',
                 self.flowDirection.toElement('flowDirection'),
                 self.totalPressure.toElement('totalPressure'),
                 self.totalTemperature.toElement('totalTemperature'))
