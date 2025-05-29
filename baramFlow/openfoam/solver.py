#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from baramFlow.coredb.coredb import CoreDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import MultiphaseModel, ModelsDB
from baramFlow.coredb.region_db import RegionDB, CavitationModel, REGION_XPATH


class SolverNotFound(Exception):
    pass


def findSolver():
    if GeneralDB.isDensityBased():
        if GeneralDB.isTimeTransient():
            return 'UTSLAeroFoam'
        else:
            return 'TSLAeroFoam'

    db = CoreDB()
    if ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID:
        for rname in db.getRegions():  # number of regions might be 1 for multiphase case
            numPhases = len(RegionDB.getSecondaryMaterials(rname)) + 1  # secondary materials + primary material
            if numPhases > 2:
                return 'multiphaseInterFoam'

            cavitationModel = db.getValue(
                RegionDB.getXPath(rname) + '/phaseInteractions/massTransfers/massTransfer[mechanism="cavitation"]/cavitation/model')
            if cavitationModel != CavitationModel.NONE.value:
                if db.exists(REGION_XPATH + '/cellZones/cellZone[zoneType="slidingMesh"]'):
                    return 'interPhaseChangeDyMFoam'
                else:
                    return 'interPhaseChangeFoam'

        return 'interFoam'

    isTimeTransient = GeneralDB.isTimeTransient()

    if RegionDB.isMultiRegion():
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
