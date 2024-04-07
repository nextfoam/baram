#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd

from baramFlow.coredb.coredb_reader import CoreDBReader
from resources import resource

availableSolvers = pd.read_csv(resource.file('openfoam/solvers.dat'), header=0, index_col=0).transpose().to_dict()


class SolverNotFound(Exception):
    pass


def findSolvers() -> list[str]:
    db = CoreDBReader()

    timeTransient   = db.getValue('.//general/timeTransient')  # noqa E221
    flowType        = db.getValue('.//general/flowType')       # noqa E221
    solverType      = db.getValue('.//general/solverType')     # noqa E221
    energyModel     = db.getValue('.//models/energyModels')    # noqa E221
    gravityDisabled = all([v == 0.0 for v in db.getVector('.//operatingConditions/gravity/direction')])  # noqa E221
    speciesModel    = db.getValue('.//models/speciesModels')           # noqa E221
    multiphaseModel = db.getValue('.//models/multiphaseModels/model')  # noqa E221

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


def findSolver():
    solvers = findSolvers()
    if len(solvers) == 1:
        return solvers[0]
    else:
        raise SolverNotFound

