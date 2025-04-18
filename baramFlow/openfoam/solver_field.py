#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.material_db import MaterialDB
from baramFlow.base.field import AGE, DENSITY, HEAT_TRANSFER_COEFF, MACH_NUMBER, MODIFIED_TURBULENT_VISCOSITY, PRESSURE, Q, SPECIFIC_DISSIPATION_RATE, TEMPERATURE, TOTAL_PRESSURE, TURBULENT_DISSIPATION_RATE, TURBULENT_KINETIC_ENERGY, VELOCITY, VORTICITY, WALL_HEAT_FLUX, WALL_SHEAR_STRESS, WALL_Y_PLUS, SpecieField, UserScalarField
from baramFlow.base.field import BasicField, CollateralField, Field, GeometryField, PhaseField
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.openfoam.solver import usePrgh


SOLVER_FIELDS = {
    PRESSURE: 'p',
    VELOCITY: 'U',
    TURBULENT_KINETIC_ENERGY: 'k',
    TURBULENT_DISSIPATION_RATE: 'epsilon',
    SPECIFIC_DISSIPATION_RATE: 'omega',
    MODIFIED_TURBULENT_VISCOSITY: 'nuTilda',
    TEMPERATURE: 'T',
    DENSITY: 'rho',
    AGE: 'age',
    HEAT_TRANSFER_COEFF: 'heatTransferCoeff',
    MACH_NUMBER: 'machNumber',
    Q: 'Q',
    TOTAL_PRESSURE: 'totalPressure',
    VORTICITY: 'vorticity',
    WALL_HEAT_FLUX: 'wallHeatFlux',
    WALL_SHEAR_STRESS: 'wallShearStress',
    WALL_Y_PLUS: 'wallYPlus'
}

def getSolverFieldName(field: Field) -> str:
    if isinstance(field, GeometryField):
        return None
    elif isinstance(field, BasicField) or isinstance(field, CollateralField):
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