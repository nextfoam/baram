#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd

from baramFlow.coredb import coredb
from resources import resource

availableSolvers = pd.read_csv(resource.file('openfoam/solvers.csv'), header=0, index_col=0).transpose().to_dict()


def findSolvers() -> list[str]:
    db = coredb.CoreDB()

    timeTransient   = db.retrieveValue('.//general/timeTransient')
    flowType        = db.retrieveValue('.//general/flowType')
    solverType      = db.retrieveValue('.//general/solverType')
    energyModel     = db.retrieveValue('.//models/energyModels')
    gravityDisabled = all([v == 0.0 for v in db.getVector('.//operatingConditions/gravity/direction')])
    speciesModel    = db.retrieveValue('.//models/speciesModels')
    multiphaseModel = db.retrieveValue('.//models/multiphaseModels/model')

    pcs = []  # problem conditions

    if solverType == 'densityBased':
        pcs.append('solverTypeDensity')
    else:  # pressure-based
        pcs.append('solverTypePressure')

    if timeTransient == 'true':
        pcs.append('timeTransient')
    else:  # steady
        pcs.append('timeSteady')

    if flowType == 'compressible':
        pcs.append('flowTypeCompressible')
    else:  # incompressible
        pcs.append('flowTypeIncompressible')

    if energyModel == 'off':
        pcs.append('energyOff')
    else:
        pcs.append('energyOn')

    if gravityDisabled:
        pcs.append('gravityOff')
    else:  # gravity enabled
        pcs.append('gravityOn')

    if speciesModel == 'off':
        pcs.append('speciesSingle')
    else:
        pcs.append('speciesMultiple')

    if multiphaseModel == 'off':
        pcs.append('phaseSingle')
    elif multiphaseModel == 'volumeOfFluid':
        pcs.append('phaseVOF')
    elif multiphaseModel == 'cavitation':
        pcs.append('phaseCavitation')

    numRegions = len(db.getRegions())
    if numRegions > 1:  # multi-region
        pcs.append('regionMultiple')
    else:
        pcs.append('regionSingle')

    solvers = []
    for sol, cap in availableSolvers.items():
        if all([cap[p] for p in pcs]):
            solvers.append(sol)
            break

    return solvers


def getSolverCapability(name: str) -> dict:
    return availableSolvers[name]
