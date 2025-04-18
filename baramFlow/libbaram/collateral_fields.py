#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import uuid
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.base.field import AGE, HEAT_TRANSFER_COEFF, MACH_NUMBER, Q, TOTAL_PRESSURE, VORTICITY, WALL_HEAT_FLUX, WALL_SHEAR_STRESS, WALL_Y_PLUS, CollateralField, Field
from baramFlow.openfoam import parallel
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.function_objects import FoDict
from baramFlow.openfoam.function_objects.collateral_fields import foAgeReport, foHeatTransferCoefficientReport, foMachNumberReport, foQReport, foTotalPressureReport, foVorticityReport, foWallHeatFluxReport, foWallShearStressReport, foWallYPlusReport
from baramFlow.openfoam.solver import findSolver
from libbaram.run import runParallelUtility


def _buildDict(fields: list[Field]) -> dict:
    functions = {}

    db = CoreDBReader()
    for rname in db.getRegions():

        if HEAT_TRANSFER_COEFF in fields:
            plainWalls  = [bcname for _, bcname in BoundaryDB.getBoundaryConditionsByType(BoundaryType.WALL, rname)]
            thermowalls = [bcname for _, bcname in BoundaryDB.getBoundaryConditionsByType(BoundaryType.THERMO_COUPLED_WALL, rname)]
            patches = plainWalls + thermowalls
            functions[f'collateralHeatTransferCoefficient_{rname}'] = foHeatTransferCoefficientReport(rname, patches)

        if WALL_HEAT_FLUX in fields:
            functions[f'collateralWallHeatFlux_{rname}'] = foWallHeatFluxReport(rname)

        region = db.getRegionProperties(rname)

        if not region.isFluid():
            continue

        # Fields only in Fluids

        if AGE in fields:
            functions[f'collateralAge_{rname}'] = foAgeReport(rname)

        if MACH_NUMBER in fields:
            functions[f'collateralMachNumber_{rname}'] = foMachNumberReport(rname)

        if Q in fields:
            functions[f'collateralQ_{rname}'] = foQReport(rname)

        if TOTAL_PRESSURE in fields:
            functions[f'collateralTotalPressure_{rname}'] = foTotalPressureReport(rname)

        if VORTICITY in fields:
            functions[f'collateralVorticity_{rname}'] = foVorticityReport(rname)

        if WALL_SHEAR_STRESS in fields:
            functions[f'collateralWallShearStress_{rname}'] = foWallShearStressReport(rname)

        if WALL_Y_PLUS in fields:
            functions[f'collateralWallYPlus_{rname}'] = foWallYPlusReport(rname)

    return {'functions': functions}


async def _calculateAgeField(times: list[str] = None):
    data = _buildDict([AGE])

    foDict = FoDict(f'delete_me_{str(uuid.uuid4())}').build(data)
    foDict.write()

    caseRoot = FileSystem.caseRoot()
    solver = findSolver()
    dictRelativePath = Path(os.path.relpath(foDict.fullPath(), caseRoot)).as_posix()  # "as_posix()": OpenFOAM cannot handle double backward slash separators in parallel processing

    if times is None:
        times = FileSystem.times()

    for time in times:
        args = ['-postProcess', '-time', time,'-dict', str(dictRelativePath)]
        proc = await runParallelUtility(
            solver, *args,
            parallel=parallel.getEnvironment(), cwd=caseRoot)

        rc = await proc.wait()
        if rc != 0:
            return rc

    foDict.fullPath().unlink()

    return 0


async def calculateCollateralField(fields: list[Field], times: list[str] = None) -> int:
    if len(fields) == 0:
        raise AssertionError

    if not all([isinstance(f, CollateralField) for f in fields]):
        raise AssertionError

    if AGE in fields and (times is None or len(times) > 1):
        await _calculateAgeField(times)
        fields.remove(AGE)

    data = _buildDict(fields)

    foDict = FoDict(f'delete_me_{str(uuid.uuid4())}').build(data)
    foDict.write()

    caseRoot = FileSystem.caseRoot()
    solver = findSolver()
    dictRelativePath = Path(os.path.relpath(foDict.fullPath(), caseRoot)).as_posix()  # "as_posix()": OpenFOAM cannot handle double backward slash separators in parallel processing

    if times is None:
        args = ['-postProcess', '-dict', str(dictRelativePath)]
    else:
        args = ['-postProcess', '-time', ','.join(times),'-dict', str(dictRelativePath)]

    proc = await runParallelUtility(
        solver, *args,
        parallel=parallel.getEnvironment(), cwd=caseRoot)

    rc = await proc.wait()

    foDict.fullPath().unlink()

    return rc
