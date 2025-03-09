#!/usr/bin/env python
# -*- coding: utf-8 -*-


from enum import Enum, IntFlag

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import MaterialType, Phase
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB


class FieldCategory(Enum):
    GEOMETRY    = 'geometry'
    BASIC       = 'basic'
    COLLATERAL  = 'collateral'
    PHASE       = 'phase'
    SPECIE      = 'specie'
    USER_SCALAR = 'userScalar'


class FieldType(Enum):
    VECTOR = 'vector'
    SCALAR = 'scalar'


class VectorComponent(IntFlag):
    MAGNITUDE = 1
    X         = 2
    Y         = 4
    Z         = 8


class Field:
    def __init__(self, category: FieldCategory, codeName: str, type_: FieldType):
        self._category = category
        self._codeName = codeName
        self._type = type_

    @property
    def category(self):
        return self._category.value

    @property
    def codeName(self):
        return self._codeName

    @property
    def type(self):
        return self._type


    # To make all Field instances with same category and codeName equal
    def __hash__(self):
        return hash((self._category, self._codeName))

    # To make all Field instances with same category and codeName equal
    def __eq__(self, other):
        return (self._category, self._codeName) == (other._category, other._codeName)


class GeometryField(Field):
    def __init__(self, codeName: str, type_: FieldType = FieldType.SCALAR):
        super().__init__(FieldCategory.GEOMETRY, codeName, type_)


class BasicField(Field):
    def __init__(self, codeName: str, type_: FieldType = FieldType.SCALAR):
        super().__init__(FieldCategory.BASIC, codeName, type_)


class CollateralField(Field):
    def __init__(self, codeName: str, type_: FieldType = FieldType.SCALAR):
        super().__init__(FieldCategory.COLLATERAL, codeName, type_)


class PhaseField(Field):
    def __init__(self, codeName: str):
        super().__init__(FieldCategory.PHASE, codeName, FieldType.SCALAR)


class SpecieField(Field):
    def __init__(self, codeName: str):
        super().__init__(FieldCategory.SPECIE, codeName, FieldType.SCALAR)


class UserScalarField(Field):
    def __init__(self, codeName: str):
        super().__init__(FieldCategory.USER_SCALAR, codeName, FieldType.SCALAR)



COORDINATE = GeometryField('Coordinate', FieldType.VECTOR)

PRESSURE   = BasicField('pressure')

VELOCITY = BasicField('Velocity', FieldType.VECTOR)


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
VORTICITY           = CollateralField('vorticity', FieldType.VECTOR)
WALL_HEAT_FLUX      = CollateralField('wallHeatFlux')
WALL_SHEAR_STRESS   = CollateralField('wallShearStress', FieldType.VECTOR)
WALL_Y_PLUS         = CollateralField('wallYPlus')


FIELD_TEXTS = {
    COORDINATE: QCoreApplication.translate('PostField', 'Coordinate'),
    PRESSURE: QCoreApplication.translate('PostField', 'Pressure'),
    VELOCITY: QCoreApplication.translate('PostField', 'Velocity'),
    TURBULENT_KINETIC_ENERGY: QCoreApplication.translate('PostField', 'Turbulent Kinetic Energy'),
    TURBULENT_DISSIPATION_RATE: QCoreApplication.translate('PostField', 'Turbulent Dissipation Rate'),
    SPECIFIC_DISSIPATION_RATE: QCoreApplication.translate('PostField', 'Specific Dissipation Rate'),
    MODIFIED_TURBULENT_VISCOSITY: QCoreApplication.translate('PostField', 'Modified Turbulent Viscosity'),
    TEMPERATURE: QCoreApplication.translate('PostField', 'Temperature'),
    DENSITY: QCoreApplication.translate('PostField', 'Density'),
    AGE: QCoreApplication.translate('PostField', 'Age'),
    HEAT_TRANSFER_COEFF: QCoreApplication.translate('PostField', 'Heat Transfer Coefficient'),
    MACH_NUMBER: QCoreApplication.translate('PostField', 'Mach Number'),
    Q: QCoreApplication.translate('PostField', 'Q'),
    TOTAL_PRESSURE: QCoreApplication.translate('PostField', 'Total Pressure'),
    VORTICITY: QCoreApplication.translate('PostField', 'Vorticity'),
    WALL_HEAT_FLUX: QCoreApplication.translate('PostField', 'Wall Heat Flux'),
    WALL_SHEAR_STRESS: QCoreApplication.translate('PostField', 'Wall Shear Stress'),
    WALL_Y_PLUS: QCoreApplication.translate('PostField', 'Wall Y Plus'),
}


VECTOR_COMPONENT_TEXTS = {
    VectorComponent.MAGNITUDE: QCoreApplication.translate('PostField', 'Magnitude'),
    VectorComponent.X: QCoreApplication.translate('PostField', 'X Component'),
    VectorComponent.Y: QCoreApplication.translate('PostField', 'Y Component'),
    VectorComponent.Z: QCoreApplication.translate('PostField', 'Z Component'),
}


def getFieldInstance(categoryStr: str, codeName: str, *args, **kwargs):
    category = FieldCategory(categoryStr)
    if category == FieldCategory.GEOMETRY:
        return GeometryField(codeName, *args, **kwargs)
    elif category == FieldCategory.BASIC:
        return BasicField(codeName, *args, **kwargs)
    elif category == FieldCategory.COLLATERAL:
        return CollateralField(codeName, *args, **kwargs)
    elif category == FieldCategory.PHASE:
        return PhaseField(codeName, *args, **kwargs)
    elif category == FieldCategory.SPECIE:
        return SpecieField(codeName, *args, **kwargs)
    elif category == FieldCategory.USER_SCALAR:
        return UserScalarField(codeName, *args, **kwargs)
    else:
        raise AssertionError


def getAvailableFields() -> list[Field]:
    fields = []

    # Always available fields

    fields.append(PRESSURE)

    fields.append(VELOCITY)

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
        for mid, _, _, phase in MaterialDB.getMaterials():
            if phase != Phase.SOLID.value:
                fields.append(PhaseField(mid))

    elif ModelsDB.isSpeciesModelOn():
        for mid, _, _, _ in MaterialDB.getMaterials(MaterialType.MIXTURE.value):
            for sid in MaterialDB.getSpecies(mid):
                fields.append(SpecieField(sid))

    for sid, _ in coredb.CoreDB().getUserDefinedScalars():
        fields.append(SpecieField(sid))

    return fields

