#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum


UNIVERSAL_GAS_CONSTANT = 8314.46261815324  # J / ( K · kmol )

MATERIALS_XPATH = '/materials'
MATERIAL_XPATH = '/materials/material'


class Phase(Enum):
    GAS = 'gas'
    LIQUID = 'liquid'
    SOLID = 'solid'


class MaterialType(Enum):
    NONMIXTURE = 'nonmixture'
    MIXTURE = 'mixture'
    SPECIE = 'specie'


class SpecificHeatSpecification(Enum):
    CONSTANT = 'constant'
    POLYNOMIAL = 'polynomial'
    JANAF = 'janaf'
    TABLE = 'table'


class DensitySpecification(Enum):
    CONSTANT = 'constant'
    PERFECT_GAS = 'perfectGas'
    POLYNOMIAL = 'polynomial'
    INCOMPRESSIBLE_PERFECT_GAS = 'incompressiblePerfectGas'
    REAL_GAS_PENG_ROBINSON = 'PengRobinsonGas'
    BOUSSINESQ = 'boussinesq'
    PERFECT_FLUID = 'perfectFluid'
    TABLE = 'table'


class TransportSpecification(Enum):
    CONSTANT = 'constant'
    SUTHERLAND = 'sutherland'
    POLYNOMIAL = 'polynomial'
    CROSS_POWER_LAW = 'cross'
    HERSCHEL_BULKLEY = 'herschelBulkley'
    BIRD_CARREAU = 'carreau'
    POWER_LAW = 'nonNewtonianPowerLaw'
    TABLE = 'table'


NON_NEWTONIAN_VISCOSITY_SPECIFICATIONS = [TransportSpecification.CROSS_POWER_LAW,
                                          TransportSpecification.HERSCHEL_BULKLEY,
                                          TransportSpecification.BIRD_CARREAU,
                                          TransportSpecification.POWER_LAW]
