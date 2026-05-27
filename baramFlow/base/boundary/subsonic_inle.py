#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from baramFlow.base.base import Vector
from baramFlow.coredb.libdb import E


@dataclass
class SubsonicInlet:
    flowDirection: Vector
    totalPressure: str
    totalTemperature: str

    def toElement(self):
        return E('subsonicInlet',
                 self.flowDirection.toElement('flowDirection'),
                 E('totalPressure',     self.totalPressure),
                 E('totalTemperature',  self.totalTemperature))
