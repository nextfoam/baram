#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.constants import VectorComponent
from baramFlow.base.field import AGE, COORDINATE, DENSITY, HEAT_TRANSFER_COEFF, MACH_NUMBER, INTERMITTENCY
from baramFlow.base.field import MODIFIED_TURBULENT_VISCOSITY, PRESSURE, Q, SPECIFIC_DISSIPATION_RATE
from baramFlow.base.field import TEMPERATURE, TOTAL_PRESSURE, TURBULENT_DISSIPATION_RATE, TURBULENT_KINETIC_ENERGY
from baramFlow.base.field import VELOCITY, VORTICITY, WALL_HEAT_FLUX, WALL_SHEAR_STRESS, WALL_Y_PLUS
from baramFlow.base.field import CELSIUS_TEMPERATURE, TRANSITION_ONSET_MOMENTUM_THICKNESS_RE
from baramFlow.base.field import BasicField, CollateralField, Field, GeometryField, PhaseField, SpecieField
from baramFlow.base.field import UserScalarField
from baramFlow.base.material.material import Phase
from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.openfoam.solver import usePrgh


SOLVER_FIELDS = {
    COORDINATE                              : 'coord',
    PRESSURE                                : 'p',
    VELOCITY                                : 'U',
    TURBULENT_KINETIC_ENERGY                : 'k',
    TURBULENT_DISSIPATION_RATE              : 'epsilon',
    SPECIFIC_DISSIPATION_RATE               : 'omega',
    MODIFIED_TURBULENT_VISCOSITY            : 'nuTilda',
    INTERMITTENCY                           : 'gammaInt',
    TRANSITION_ONSET_MOMENTUM_THICKNESS_RE  : 'ReThetat',
    TEMPERATURE                             : 'T',
    CELSIUS_TEMPERATURE                     : 'TCelsius',
    DENSITY                                 : 'rho',
    AGE                                     : 'age',
    HEAT_TRANSFER_COEFF                     : 'heatTransferCoeff',
    MACH_NUMBER                             : 'Mach',
    Q                                       : 'Q',
    TOTAL_PRESSURE                          : 'totalPressure',
    VORTICITY                               : 'vorticity',
    WALL_HEAT_FLUX                          : 'wallHeatFlux',
    WALL_SHEAR_STRESS                       : 'wallShearStress',
    WALL_Y_PLUS                             : 'yPlus'
}

def getSolverFieldName(field: Field) -> str:
    if isinstance(field, GeometryField) or isinstance(field, BasicField) or isinstance(field, CollateralField):
        if field == PRESSURE:
            try:
                if usePrgh():
                    return 'p_rgh'
            except RuntimeError:
                pass

        return SOLVER_FIELDS[field]
    elif isinstance(field, PhaseField):
        return 'alpha.' + MaterialDB.getName(field.codeName)
    elif isinstance(field, SpecieField):
        return MaterialDB.getName(field.codeName)
    elif isinstance(field, UserScalarField):
        return UserDefinedScalarsDB.getFieldName(field.codeName)


def getSolverComponentName(field: Field, component: VectorComponent) -> str:
    solverFieldName = getSolverFieldName(field)
    if component == VectorComponent.MAGNITUDE:
        return f'mag({solverFieldName})'
    elif component == VectorComponent.X:
        return f'{solverFieldName}x'
    elif component == VectorComponent.Y:
        return f'{solverFieldName}y'
    elif component == VectorComponent.Z:
        return f'{solverFieldName}z'
    else:  # No way to reach here
        return ''


def getAvailableFlowFields():
    fields = [PRESSURE, VELOCITY]

    # Fields depending on the turbulence model
    rasModel = TurbulenceModelsDB.getRASModel()
    if rasModel == TurbulenceModel.K_EPSILON or TurbulenceModelsDB.isLESKEqnModel():
        fields.append(TURBULENT_KINETIC_ENERGY)
        fields.append(TURBULENT_DISSIPATION_RATE)
    elif rasModel == TurbulenceModel.K_OMEGA:
        fields.append(TURBULENT_KINETIC_ENERGY)
        fields.append(SPECIFIC_DISSIPATION_RATE)
    elif rasModel == TurbulenceModel.TRANSITION_SST:
        fields.append(TURBULENT_KINETIC_ENERGY)
        fields.append(SPECIFIC_DISSIPATION_RATE)
        fields.append(INTERMITTENCY)
        fields.append(TRANSITION_ONSET_MOMENTUM_THICKNESS_RE)
    elif rasModel == TurbulenceModel.SPALART_ALLMARAS:
        fields.append(MODIFIED_TURBULENT_VISCOSITY)

    # Fields depending on the energy model
    # if ModelsDB.isEnergyModelOn():
    #     fields.append(TEMPERATURE)
    #     fields.append(DENSITY)

    # Material fields on multiphase model
    if ModelsDB.isMultiphaseModelOn():
        for mid, _, _, phase in MaterialDB.getMaterials():
            if phase == Phase.SOLID.value:
                continue

            field = PhaseField(mid)
            fields.append(field)

    elif ModelsDB.isSpeciesModelOn():
        for mixture, _ in RegionDB.getMixturesInRegions():
            for sid in MaterialDB.getSpecies(mixture):
                fields.append(SpecieField(sid))

    return fields


def getAvailableFields(includeCoordinate=False) -> list[Field]:
    fields = getAvailableFlowFields()

    # Always available fields

    if includeCoordinate:
        fields.append(COORDINATE)

    fields.append(Q)
    fields.append(TOTAL_PRESSURE)
    fields.append(VORTICITY)
    fields.append(WALL_HEAT_FLUX)
    fields.append(WALL_SHEAR_STRESS)
    fields.append(WALL_Y_PLUS)

    if not GeneralDB.isTimeTransient() and not GeneralDB.isDensityBased():
        fields.append(AGE)

    # Fields depending on the energy model
    energyOn = ModelsDB.isEnergyModelOn()
    if energyOn:
        fields.append(TEMPERATURE)
        fields.append(CELSIUS_TEMPERATURE)
        fields.append(DENSITY)
        fields.append(HEAT_TRANSFER_COEFF)
        fields.append(MACH_NUMBER)

    for sid, _ in coredb.CoreDB().getUserDefinedScalars():
        fields.append(UserScalarField(str(sid)))

    return fields


