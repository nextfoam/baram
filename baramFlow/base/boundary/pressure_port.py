#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from libbaram.pfloat import PFloat

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.coredb import _CoreDB
from baramFlow.coredb.libdb import E


@dataclass
class PressureInlet:
    pressure: str

    def applyToDB(self, db: _CoreDB, bcid: str):
        db.setValue(BoundaryDB.getXPath(bcid) + '/pressureInlet/pressure', self.pressure)


@dataclass
class PressureOutlet:
    totalPressure: PFloat
    nonReflective: bool
    calculatedBackflow: bool
    backflowTotalTemperature: PFloat = field(default_factory=lambda: PFloat('300'))

    def toElement(self):
        return E('pressureOutlet',
                 self.totalPressure.toElement('totalPressure'),
                 E('nonReflective', self.nonReflective),
                 E('calculatedBackflow', self.calculatedBackflow),
                 self.backflowTotalTemperature.toElement('backflowTotalTemperature'))
