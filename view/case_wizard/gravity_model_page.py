#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QWizardPage

from .gravity_model_page_ui import Ui_GravityModelPage


class GravityModelPage(QWizardPage):
    MAX_GRAVITY =  200.0  # (m/s2)
    MIN_GRAVITY = -200.0  # (m/s2)
    DECIMAL_PRECISION = 4  # Digits after decimal point

    def __init__(self, *args, **kwargs):
        super(GravityModelPage, self).__init__(*args, **kwargs)

        self._ui = Ui_GravityModelPage()
        self._ui.setupUi(self)

        self._ui.NotInclude.setChecked(True)
        self._ui.GXValue.setEnabled(False)
        self._ui.GYValue.setEnabled(False)
        self._ui.GZValue.setEnabled(False)

        self._ui.GXValue.setValidator(QDoubleValidator(self.MIN_GRAVITY, self.MAX_GRAVITY, self.DECIMAL_PRECISION))
        self._ui.GYValue.setValidator(QDoubleValidator(self.MIN_GRAVITY, self.MAX_GRAVITY, self.DECIMAL_PRECISION))
        self._ui.GZValue.setValidator(QDoubleValidator(self.MIN_GRAVITY, self.MAX_GRAVITY, self.DECIMAL_PRECISION))


