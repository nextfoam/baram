#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb.models_db import TurbulenceModel, ModelsDB
from view.widgets.volume_fraction_widget import VolumeFractionWidget
from .turbulence_k_epsilon_widget import TurbulenceKEpsilonWidget
from .turbulence_k_omega_widget import TurbulenceKOmegaWidget
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
    _TURBULENCE_WIDGETS = {
        TurbulenceModel.INVISCID: None,
        TurbulenceModel.LAMINAR: None,
        TurbulenceModel.K_EPSILON: TurbulenceKEpsilonWidget,
        TurbulenceModel.K_OMEGA: TurbulenceKOmegaWidget,
        TurbulenceModel.SPALART_ALLMARAS: TurbulenceSpalartAllmarasWidget,
        TurbulenceModel.LES: None,
    }

    @classmethod
    def turbulenceWidget(cls, xpath, layout):
        widgetClass = cls._TURBULENCE_WIDGETS[ModelsDB.getTurbulenceModel()]
        if widgetClass is not None:
            widget = widgetClass(xpath)
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
    def volumeFractionWidget(cls, region, xpath, layout):
        widget = VolumeFractionWidget(region, xpath)
        if widget.on():
            layout.addWidget(widget)

        return widget
