#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage
from PySide6.QtGui import QDoubleValidator

from .gravity_model_page_ui import Ui_GravityModelPage


class GravityModelPage(QWizardPage):
    MIN_GRAVITY = -200.0  # (m/s2)
    MAX_GRAVITY = 200.0  # (m/s2)
    DECIMAL_PRECISION = 4  # Digits after decimal point

    def __init__(self, *args, **kwargs):
        super(GravityModelPage, self).__init__(*args, **kwargs)

        self._ui = Ui_GravityModelPage()
        self._ui.setupUi(self)

        self._ui.notInclude.setChecked(True)

        self._ui.x.setText('0.0')
        self._ui.y.setText('-9.81')
        self._ui.z.setText('0.0')

        self._ui.x.setEnabled(False)
        self._ui.y.setEnabled(False)
        self._ui.z.setEnabled(False)

        self._ui.x.setValidator(QDoubleValidator(self.MIN_GRAVITY, self.MAX_GRAVITY, self.DECIMAL_PRECISION))
        self._ui.y.setValidator(QDoubleValidator(self.MIN_GRAVITY, self.MAX_GRAVITY, self.DECIMAL_PRECISION))
        self._ui.z.setValidator(QDoubleValidator(self.MIN_GRAVITY, self.MAX_GRAVITY, self.DECIMAL_PRECISION))

        self.registerField('gravityInclude', self._ui.include)
        self.registerField('gravityX', self._ui.x)
        self.registerField('gravityY', self._ui.y)
        self.registerField('gravityZ', self._ui.z)


