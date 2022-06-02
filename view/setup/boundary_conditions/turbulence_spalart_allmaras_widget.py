#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget

from .turbulence_spalart_allmaras_widget_ui import Ui_turbulenceSpalartAllmarasWidget


class SpecificationMethod(Enum):
    MODIFIED_TURBULENT_VISCOSITY = 0
    TURBULENT_VISCOSITY_RATIO = auto()


class TurbulenceSpalartAllmarasWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self._ui = Ui_turbulenceSpalartAllmarasWidget()

        self._parent = parent

        self._ui.setupUi(self)
        self._connectSignalsSlots()

        self._specificationMethodChanged(0)

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._specificationMethodChanged)

    def _specificationMethodChanged(self, index):
        self._ui.modifiedTurbulentViscosity.setVisible(
            index == SpecificationMethod.MODIFIED_TURBULENT_VISCOSITY.value)
        self._ui.turbulentViscosityRatio.setVisible(
            index == SpecificationMethod.TURBULENT_VISCOSITY_RATIO.value)
