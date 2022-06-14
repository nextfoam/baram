#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.setup.models.models_db import TurbulenceModel, ModelsDB
from .turbulence_k_epsilon_widget import TurbulenceKEpsilonWidget
from .turbulence_k_omega_widget import TurbulenceKOmegaWidget
from .turbulence_spalart_allmaras_widget import TurbulenceSpalartAllmarasWidget


class TurbulenceModelHelper:
    _WIDGETS = {
        TurbulenceModel.INVISCID: None,
        TurbulenceModel.LAMINAR: None,
        TurbulenceModel.K_EPSILON: TurbulenceKEpsilonWidget,
        TurbulenceModel.K_OMEGA: TurbulenceKOmegaWidget,
        TurbulenceModel.SPALART_ALLMARAS: TurbulenceSpalartAllmarasWidget,
        TurbulenceModel.LES: None,
    }

    @classmethod
    def createWidget(cls, xpath):
        widgetClass = cls._WIDGETS[ModelsDB.getTurbulenceModel()]
        if widgetClass is not None:
            return widgetClass(xpath)
        else:
            return None
