#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.base.model.model import DPMParticleType
from baramFlow.coredb.coredb import CoreDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import MultiphaseModel, ModelsDB
from baramFlow.coredb.region_db import RegionDB, CavitationModel, REGION_XPATH


class SolverNotFound(Exception):
    pass


def findSolver():
    isTimeTransient = GeneralDB.isTimeTransient()

    if GeneralDB.isDensityBased():
        if isTimeTransient:
            return 'UTSLAeroFoam'
        else:
            return 'TSLAeroFoam'

    db = CoreDB()

    dpmModel = DPMModelManager.particleType()
    if dpmModel == DPMParticleType.INERT:
        if isTimeTransient:
            return 'thermoParcelBuoyantPimpleNFoam'
        else:
            return 'thermoParcelBuoyantSimpleNFoam'

    if dpmModel == DPMParticleType.DROPLET:
        return 'reactingParcelFoam'

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
