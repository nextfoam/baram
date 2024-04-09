#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.models_db import TurbulenceModel, ModelsDB, TurbulenceModelsDB, SubgridScaleModel
from baramFlow.view.widgets.volume_fraction_widget import VolumeFractionWidget
from .turbulence_k_epsilon_widget import TurbulenceKEpsilonWidget
from .turbulence_k_omega_widget import TurbulenceKOmegaWidget
from .turbulence_LES_widget import TurbulenceLESWidget
from .turbulence_spalart_allmaras_widget import TurbulenceSpalartAllmarasWidget
from .temperature_widget import TemperatureWidget


class EmptyWidget:
    def __init__(self):
        return

    def on(self):
        return False

    def appendToWriter(self, writer):
        return True

    def load(self):
        return


class ConditionalWidgetHelper:
    @classmethod
    def turbulenceWidget(cls, xpath, layout):
        turbulenceModel = ModelsDB.getTurbulenceModel()

        widget = None
        if turbulenceModel == TurbulenceModel.K_EPSILON:
            widget = TurbulenceKEpsilonWidget(xpath)
        elif turbulenceModel == TurbulenceModel.K_OMEGA:
            widget = TurbulenceKOmegaWidget(xpath)
        elif turbulenceModel == TurbulenceModel.SPALART_ALLMARAS:
            widget = TurbulenceSpalartAllmarasWidget(xpath)
        elif turbulenceModel == TurbulenceModel.LES:
            if TurbulenceModelsDB.getLESSubgridScaleModel() in (SubgridScaleModel.DYNAMIC_KEQN, SubgridScaleModel.KEQN):
                widget = TurbulenceLESWidget(xpath)

        if widget:
            layout.addWidget(widget)
        else:
            widget = EmptyWidget()

        return widget

    @classmethod
    def temperatureWidget(cls, xpath, bcid, layout):
        widget = TemperatureWidget(xpath, bcid)
        if widget.on():
            layout.addWidget(widget)

        return widget

    @classmethod
    def volumeFractionWidget(cls, rname, xpath, layout):
        widget = VolumeFractionWidget(rname, xpath)
        if widget.on():
            layout.addWidget(widget)

        return widget
