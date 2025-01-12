#!/usr/bin/env python
# -*- coding: utf-8 -*-


from dataclasses import dataclass, field
from enum import Enum

from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import MaterialType, Phase
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.openfoam.solver import usePrgh


class FieldType(Enum):
    BASIC       = 'basic'
    COLLATERAL  = 'collateral'
    PHASE       = 'phase'
    SPECIE      = 'specie'
    USER_SCALAR = 'userScalar'


class Field:
    def __init__(self, name):
        self._type: FieldType = FieldType.BASIC
        self._name: str = name

    @property
    def type(self):
        return self._type.value

    @property
    def name(self):
        return self._name

    def __hash__(self):
        return hash((self._type, self.name))

    def __eq__(self, other):
        return (self._type, self.name) == (other._type, other.name)

class BasicField(Field):
    def __init__(self, name):
        super().__init__(name)
        self._type = FieldType.BASIC

class CollateralField(Field):
    def __init__(self, name):
        super().__init__(name)
        self._type = FieldType.COLLATERAL

class PhaseField(Field):
    def __init__(self, name):
        super().__init__(name)
        self._type = FieldType.PHASE

class SpecieField(Field):
    def __init__(self, name):
        super().__init__(name)
        self._type = FieldType.SPECIE

class UserScalarField(Field):
    def __init__(self, name):
        super().__init__(name)
        self._type = FieldType.USER_SCALAR


PRESSURE   = BasicField('pressure')
SPEED      = BasicField('speed')
X_VELOCITY = BasicField('X-Velocity')
Y_VELOCITY = BasicField('Y-Velocity')
Z_VELOCITY = BasicField('Z-Velocity')
TURBULENT_KINETIC_ENERGY     = BasicField('turbulentKineticEnergy')
TURBULENT_DISSIPATION_RATE   = BasicField('turbulentDissipationRate')
SPECIFIC_DISSIPATION_RATE    = BasicField('specificDissipationRate')
MODIFIED_TURBULENT_VISCOSITY = BasicField('modifiedTurbulentViscosity')
TEMPERATURE = BasicField('temperature')
DENSITY =     BasicField('density')

AGE                 = CollateralField('age')
HEAT_TRANSFER_COEFF = CollateralField('heatTransferCoeff')
MACH_NUMBER         = CollateralField('machNumber')
Q                   = CollateralField('Q')
TOTAL_PRESSURE      = CollateralField('totalPressure')
VORTICITY           = CollateralField('vorticity')
WALL_HEAT_FLUX      = CollateralField('wallHeatFlux')
WALL_SHEAR_STRESS   = CollateralField('wallShearStress')
WALL_Y_PLUS         = CollateralField('wallYPlus')


def getFieldInstance(type_: str, name: str, *args, **kwargs):
    fieldType = FieldType(type_)
    if fieldType == FieldType.BASIC:
        return BasicField(name, *args, **kwargs)
    elif fieldType == FieldType.COLLATERAL:
        return CollateralField(name, *args, **kwargs)
    elif fieldType == FieldType.COLLATERAL:
        return PhaseField(name, *args, **kwargs)
    elif fieldType == FieldType.COLLATERAL:
        return SpecieField(name, *args, **kwargs)
    elif fieldType == FieldType.COLLATERAL:
        return UserScalarField(name, *args, **kwargs)
    else:
        raise AssertionError


def getAvailableFields() -> list[Field]:
    fields = []

    # Always available fields
    fields.append(PRESSURE)

    fields.append(SPEED)
    fields.append(X_VELOCITY)
    fields.append(Y_VELOCITY)
    fields.append(Z_VELOCITY)

    fields.append(Q)
    fields.append(TOTAL_PRESSURE)
    fields.append(VORTICITY)
    fields.append(WALL_HEAT_FLUX)
    fields.append(WALL_SHEAR_STRESS)
    fields.append(WALL_Y_PLUS)

    if not GeneralDB.isTimeTransient() and not GeneralDB.isDensityBased():
        fields.append(AGE)

    # Fields depending on the turbulence model
    turbulenceModel = TurbulenceModelsDB.getModel()
    if turbulenceModel == TurbulenceModel.K_EPSILON:
        fields.append(TURBULENT_KINETIC_ENERGY)
        fields.append(TURBULENT_DISSIPATION_RATE)
    elif turbulenceModel == TurbulenceModel.K_OMEGA:
        fields.append(TURBULENT_KINETIC_ENERGY)
        fields.append(SPECIFIC_DISSIPATION_RATE)
    elif turbulenceModel == TurbulenceModel.SPALART_ALLMARAS:
        fields.append(MODIFIED_TURBULENT_VISCOSITY)

    # Fields depending on the energy model
    energyOn = ModelsDB.isEnergyModelOn()
    if energyOn:
        fields.append(TEMPERATURE)
        fields.append(DENSITY)
        fields.append(HEAT_TRANSFER_COEFF)
        if not GeneralDB.isDensityBased():
            fields.append(MACH_NUMBER)

    # Material fields on multiphase model
    if ModelsDB.isMultiphaseModelOn():
        for _, name, _, phase in MaterialDB.getMaterials():
            if phase != Phase.SOLID.value:
                fields.append(PhaseField(name))

    elif ModelsDB.isSpeciesModelOn():
        for mid, _, _, _ in MaterialDB.getMaterials(MaterialType.MIXTURE.value):
            for _, name in MaterialDB.getSpecies(mid).items():
                fields.append(SpecieField(name))

    for _, name in coredb.CoreDB().getUserDefinedScalars():
        fields.append(SpecieField(name))

    return fields

