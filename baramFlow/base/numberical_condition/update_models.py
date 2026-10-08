#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from libbaram.pfloat import PFloat

from baramFlow.base.numberical_condition.numberical_condition import PressureVelocityCouplingScheme
from baramFlow.base.numberical_condition.numberical_condition import DensityBasedSolverParameters
from baramFlow.base.numberical_condition.numberical_condition import DiscretizationSchemes, UnderRelaxationFactors
from baramFlow.base.numberical_condition.numberical_condition import HighOrderTermRelaxation, MultiPhase
from baramFlow.base.numberical_condition.numberical_condition import ConvergenceCriteria


@dataclass(kw_only=True)
class NumericalUpdate:
    pressureVelocityCouplingScheme: PressureVelocityCouplingScheme
    densityBasedSolverParameters: DensityBasedSolverParameters
    useMomentumPredictor: bool
    discretizationSchemes: DiscretizationSchemes
    underRelaxationFactors: UnderRelaxationFactors
    highOrderTermRelaxation: HighOrderTermRelaxation
    maxIterationsPerTimeStep: str           = '20'
    numberOfCorrectors: str                 = '4'
    numberOfNonOrthogonalCorrectors: PFloat = field(default_factory=lambda: PFloat('0'))
    multiphase: MultiPhase
    convergenceCriteria: ConvergenceCriteria
