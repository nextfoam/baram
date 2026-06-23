#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from baramFlow.base.region.regions_cache import Regions
from baramFlow.coredb.coredb import CoreDB, _CoreDB


@dataclass
class ProjectData:
    regions: Regions = field(default_factory=Regions)

    def load(self):
        db: _CoreDB = CoreDB()
        self.regions.load(db.getElement('regions'))


projectData = ProjectData()