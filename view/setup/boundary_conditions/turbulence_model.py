#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from .turbulence_k_epsilon_widget import TurbulenceKEpsilonWidget
from .turbulence_k_omega_widget import TurbulenceKOmegaWidget
from .turbulence_spalart_allmaras_widget import TurbulenceSpalartAllmarasWidget


class TurbulenceModel:
    class MODEL(Enum):
        K_EPSILON = auto()
        K_OMEGA = auto()
        SPALART_ALLMARAS = auto()

    def __init__(self, model=MODEL.SPALART_ALLMARAS):
        self._model = model

    def boundaryConditionWidget(self, parent):
        if self._model == self.MODEL.K_EPSILON:
            return TurbulenceKEpsilonWidget(parent)
        elif self._model == self.MODEL.K_OMEGA:
            return TurbulenceKOmegaWidget(parent)
        elif self._model == self.MODEL.SPALART_ALLMARAS:
            return TurbulenceSpalartAllmarasWidget(parent)
