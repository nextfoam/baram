#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget

from .turbulence_k_omega_widget_ui import Ui_turbulenceKOmegaWidget


class TurbulenceKOmegaWidget(QWidget):
    class SPECIFICATION_METHOD(Enum):
        K_AND_OMEGA = 0
        INTENSITY_AND_VISCOCITY_RATIO = auto()

    def __init__(self, parent):
        super().__init__()
        self._ui = Ui_turbulenceKOmegaWidget()

        self._parent = parent

        self._ui.setupUi(self)
        self._connectSignalsSlots()

        self._specificationMethodChanged(0)

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._specificationMethodChanged)

    def _specificationMethodChanged(self, index):
        self._ui.kAndOmega.setVisible(index == self.SPECIFICATION_METHOD.K_AND_OMEGA.value)
        self._ui.intensityAndViscocityRatio.setVisible(index == self.SPECIFICATION_METHOD.INTENSITY_AND_VISCOCITY_RATIO.value)
        self._parent._resizeDialog(self._ui.groupBox)
