#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum

from libbaram.pfloat import PFloat

from baramFlow.coredb.coredb import _CoreDB


class FlowRateSpecification(Enum):
    VOLUME_FLOW_RATE = 'volumeFlowRate'
    MASS_FLOW_RATE = 'massFlowRate'


@dataclass
class BoundaryFlowRate:
    specification: FlowRateSpecification
    volumeFlowRate: PFloat  = None
    massFlowRate: PFloat    = None

    def applyToDBByPath(self, db: _CoreDB, parentPath: str):
        xpath = parentPath + '/flowRate'
        db.setValue(xpath + '/specification', self.specification.value)
        if self.specification == FlowRateSpecification.VOLUME_FLOW_RATE:
            db.setValue(xpath + '/volumeFlowRate', str(self.volumeFlowRate))
        elif self.specification == FlowRateSpecification.MASS_FLOW_RATE:
            db.setValue(xpath + '/massFlowRate', str(self.massFlowRate))
