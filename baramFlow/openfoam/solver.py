#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from baramFlow.coredb.coredb import CoreDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import MultiphaseModel, ModelsDB
from baramFlow.coredb.region_db import RegionDB


class SolverNotFound(Exception):
    pass


def findSolver():
    if GeneralDB.isDensityBased():
        return 'TSLAeroFoam'

    if ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID:
        for rname in CoreDB().getRegions():  # number of regions might be 1 for multiphase case
            numPhases = len(RegionDB.getSecondaryMaterials(rname)) + 1  # secondary materials + primary material
            if numPhases > 2:
                return 'multiphaseInterFoam'

        return 'interFoam'

    isTimeTransient = GeneralDB.isTimeTransient()

    if RegionDB.getNumberOfRegions() > 1:
        if isTimeTransient:
            return 'chtMultiRegionPimpleNFoam'
        else:
            return 'chtMultiRegionSimpleNFoam'

    if isTimeTransient:
        return 'buoyantPimpleNFoam'
    else:
        return 'buoyantSimpleNFoam'


def usePrgh() -> bool:
    if GeneralDB.isDensityBased():
        return False
    else:
        return True


def useGaugePressureInPrgh() -> bool:
    if GeneralDB.isDensityBased():
        return False
    else:
        return True


def allRoundSolver() -> bool:
    if ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID:
        return True
    else:
        return False
