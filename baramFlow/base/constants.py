#!/usr/bin/env python
# -*- coding: utf-8 -*-


from enum import Enum, IntFlag


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


class Function1Type(Enum):
    CONSTANT    = "constant"
    TABLE       = "table"