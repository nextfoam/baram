#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum


class PressureVelocityCouplingScheme(Enum):
    SIMPLE = 'SIMPLE'
    SIMPLEC = 'SIMPLEC'


class ImplicitDiscretizationScheme(Enum):
    FIRST_ORDER_IMPLICIT = 'firstOrderImplicit'
    SECOND_ORDER_IMPLICIT = 'secondOrderImplicit'


class UpwindDiscretizationScheme(Enum):
    FIRST_ORDER_UPWIND = 'firstOrderUpwind'
    SECOND_ORDER_UPWIND = 'secondOrderUpwind'


class InterpolationScheme(Enum):
    LINEAR = 'linear'
    MOMENTUM_WEIGHTED_RECONSTRUC = 'momentumWeightedReconstruct'
    MOMENTUM_WEIGHTED = 'momentumWeighted'


class NumericalDB:
    NUMERICAL_CONDITIONS_XPATH = './/numericalConditions'
