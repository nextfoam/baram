#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from baramFlow.coredb.coredb import _CoreDB
from baramFlow.coredb.boundary_db import BoundaryDB


@dataclass
class OpenChannelInlet:
    volumeFlowRate: str

    def applyToDB(self, db: _CoreDB, bcid: str):
        db.setValue(BoundaryDB.getXPath(bcid) + '/openChannelInlet/volumeFlowRate', self.volumeFlowRate)


@dataclass
class OpenChannelOutlet:
    meanVelocity: str

    def applyToDB(self, db: _CoreDB, bcid: str):
        db.setValue(BoundaryDB.getXPath(bcid) + '/openChannelOutlet/meanVelocity', self.meanVelocity)
