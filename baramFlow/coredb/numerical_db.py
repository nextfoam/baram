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


class Formulation(Enum):
    IMPLICIT = 'implicit'
    EXPLICIT = 'explicit'


class FluxType(Enum):
    ROE_FDS = 'roeFlux'
    AUSM = 'AUSMplusFlux'
    AUSM_UP = 'AUSMplusUpFlux'


class NumericalDB:
    NUMERICAL_CONDITIONS_XPATH = '/numericalConditions'
    CONVERGENCE_CRITERIA_XPATH = NUMERICAL_CONDITIONS_XPATH + '/convergenceCriteria'
