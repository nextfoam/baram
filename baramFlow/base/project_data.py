#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from baramFlow.base.numberical_condition.numberical_condition import NumericalConditions
from baramFlow.base.region.regions_cache import Regions
from baramFlow.coredb.coredb import CoreDB, _CoreDB


@dataclass
class ProjectData:
    regions: Regions                            = field(default_factory=Regions)
    numericalConditions: NumericalConditions    = field(default_factory=NumericalConditions)

    def load(self):
        db: _CoreDB = CoreDB()
        self.regions.load(db.getElement('regions'))
        self.numericalConditions = NumericalConditions.fromElement(db.getElement('numericalConditions'))



projectData = ProjectData()