#!/usr/bin/env python
# -*- coding: utf-8 -*-


from enum import Enum, IntFlag

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB


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
    def category(self) -> FieldCategory:
        return self._category

    @property
    def codeName(self) -> str:
        return self._codeName

    @property
    def type(self) -> FieldType:
        return self._type

    @property
    def text(self) -> str:
        return NotImplementedError

    # To make all Field instances with same category and codeName equal
    def __hash__(self):
        return hash((self._category, self._codeName))

    # To make all Field instances with same category and codeName equal
    def __eq__(self, other):
        return (self._category, self._codeName) == (other._category, other._codeName)


class GeometryField(Field):
    def __init__(self, codeName: str, type_: FieldType = FieldType.SCALAR):
        super().__init__(FieldCategory.GEOMETRY, codeName, type_)

    @property
    def text(self) -> str:
        return _getPredefinedFieldText(self)

class BasicField(Field):
    def __init__(self, codeName: str, type_: FieldType = FieldType.SCALAR):
        super().__init__(FieldCategory.BASIC, codeName, type_)

    @property
    def text(self) -> str:
        return _getPredefinedFieldText(self)

class CollateralField(Field):
    def __init__(self, codeName: str, type_: FieldType = FieldType.SCALAR):
        super().__init__(FieldCategory.COLLATERAL, codeName, type_)

    @property
    def text(self) -> str:
        return _getPredefinedFieldText(self)

class PhaseField(Field):
    def __init__(self, codeName: str):
        super().__init__(FieldCategory.PHASE, codeName, FieldType.SCALAR)

    @property
    def text(self):
        return MaterialDB.getName(self._codeName)


class SpecieField(Field):
    def __init__(self, codeName: str):
        super().__init__(FieldCategory.SPECIE, codeName, FieldType.SCALAR)

    @property
    def text(self) -> str:
        return MaterialDB.getName(self._codeName)


class UserScalarField(Field):
    def __init__(self, codeName: str):
        super().__init__(FieldCategory.USER_SCALAR, codeName, FieldType.SCALAR)

    @property
    def text(self) -> str:
        return UserDefinedScalarsDB.getFieldName(self._codeName)


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


ALL_FIELDS: dict[tuple[FieldCategory, str], Field] = {
    (COORDINATE.category,                   COORDINATE.codeName):                   COORDINATE,
    (PRESSURE.category,                     PRESSURE.codeName):                     PRESSURE,
    (VELOCITY.category,                     VELOCITY.codeName):                     VELOCITY,
    (TURBULENT_KINETIC_ENERGY.category,     TURBULENT_KINETIC_ENERGY.codeName):     TURBULENT_KINETIC_ENERGY,
    (TURBULENT_DISSIPATION_RATE.category,   TURBULENT_DISSIPATION_RATE.codeName):   TURBULENT_DISSIPATION_RATE,
    (SPECIFIC_DISSIPATION_RATE.category,    SPECIFIC_DISSIPATION_RATE.codeName):    SPECIFIC_DISSIPATION_RATE,
    (MODIFIED_TURBULENT_VISCOSITY.category, MODIFIED_TURBULENT_VISCOSITY.codeName): MODIFIED_TURBULENT_VISCOSITY,
    (TEMPERATURE.category,                  TEMPERATURE.codeName):                  TEMPERATURE,
    (DENSITY.category,                      DENSITY.codeName):                      DENSITY,
    (AGE.category,                          AGE.codeName):                          AGE,
    (HEAT_TRANSFER_COEFF.category,          HEAT_TRANSFER_COEFF.codeName):          HEAT_TRANSFER_COEFF,
    (MACH_NUMBER.category,                  MACH_NUMBER.codeName):                  MACH_NUMBER,
    (Q.category,                            Q.codeName):                            Q,
    (TOTAL_PRESSURE.category,               TOTAL_PRESSURE.codeName):               TOTAL_PRESSURE,
    (VORTICITY.category,                    VORTICITY.codeName):                    VORTICITY,
    (WALL_HEAT_FLUX.category,               WALL_HEAT_FLUX.codeName):               WALL_HEAT_FLUX,
    (WALL_SHEAR_STRESS.category,            WALL_SHEAR_STRESS.codeName):            WALL_SHEAR_STRESS,
    (WALL_Y_PLUS.category,                  WALL_Y_PLUS.codeName):                  WALL_Y_PLUS,
}


def _getPredefinedFieldText(field: Field):
    FIELD_TEXTS = {  # This is created whenever it is called so that translation is updated
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

    return FIELD_TEXTS[field]


VECTOR_COMPONENT_TEXTS = {
    VectorComponent.MAGNITUDE: QCoreApplication.translate('PostField', 'Magnitude'),
    VectorComponent.X: QCoreApplication.translate('PostField', 'X Component'),
    VectorComponent.Y: QCoreApplication.translate('PostField', 'Y Component'),
    VectorComponent.Z: QCoreApplication.translate('PostField', 'Z Component'),
}


def getFieldInstance(categoryStr: str, codeName: str):
    category = FieldCategory(categoryStr)
    if (category, codeName) in ALL_FIELDS:
        return ALL_FIELDS[(category, codeName)]
    elif category == FieldCategory.PHASE:
        return PhaseField(codeName)
    elif category == FieldCategory.SPECIE:
        return SpecieField(codeName)
    elif category == FieldCategory.USER_SCALAR:
        return UserScalarField(codeName)
    else:
        raise AssertionError




