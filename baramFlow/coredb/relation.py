#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb import region_db, scalar_model_db, boundary_db, cell_zone_db, initialization_db, monitor_db

from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.specie_model_db import SpecieModelDB


def registerObservers():
    SpecieModelDB.registerObserver(region_db.SpecieModelObserver())

    MaterialDB.registerObserver(boundary_db.MaterialObserver())
    MaterialDB.registerObserver(region_db.MaterialObserver())
    MaterialDB.registerObserver(cell_zone_db.MaterialObserver())
    MaterialDB.registerObserver(initialization_db.MaterialObserver())
    MaterialDB.registerObserver(monitor_db.MaterialObserver())
    MaterialDB.registerObserver(scalar_model_db.MaterialObserver())

    RegionDB.registerMaterialObserver(boundary_db.RegionMaterialObserver())
    RegionDB.registerMaterialObserver(cell_zone_db.RegionMaterialObserver())
    RegionDB.registerMaterialObserver(initialization_db.RegionMaterialObserver())
