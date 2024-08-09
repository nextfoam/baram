#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import QObject, Signal

from .gravity_model_page_ui import Ui_GravityModelPage


class DoubleField(QObject):
    valueChanged = Signal(float)

    def __init__(self, editor, value):
        super().__init__()

        self._editor = editor
        self._value = None

        self._editor.textChanged.connect(self._chagned)
        self._editor.setText(value)

    def value(self):
        return self._value

    def _chagned(self, text):
        try:
            self._value = float(text)
        except ValueError:
            self._value = None

        self.valueChanged.emit(self._value)


class GravityModelPage(QWizardPage):
    MIN_GRAVITY = -200.0  # (m/s2)
    MAX_GRAVITY = 200.0  # (m/s2)
    DECIMAL_PRECISION = 4  # Digits after decimal point

    def __init__(self, *args, **kwargs):
        super(GravityModelPage, self).__init__(*args, **kwargs)

        self._ui = Ui_GravityModelPage()
        self._ui.setupUi(self)

        self._complete = False

        self._ui.include.setChecked(True)

        self._ui.include.hide()
        self._ui.notInclude.hide()

        self._x = DoubleField(self._ui.x, '0.0')
        self._y = DoubleField(self._ui.y, '0.0')
        self._z = DoubleField(self._ui.z, '0.0')

        self._x.valueChanged.connect(self.isComplete)
        self._y.valueChanged.connect(self.isComplete)
        self._z.valueChanged.connect(self.isComplete)

        # self._ui.x.setEnabled(False)
        # self._ui.y.setEnabled(False)
        # self._ui.z.setEnabled(False)

        self._ui.x.setValidator(QDoubleValidator(self.MIN_GRAVITY, self.MAX_GRAVITY, self.DECIMAL_PRECISION))
        self._ui.y.setValidator(QDoubleValidator(self.MIN_GRAVITY, self.MAX_GRAVITY, self.DECIMAL_PRECISION))
        self._ui.z.setValidator(QDoubleValidator(self.MIN_GRAVITY, self.MAX_GRAVITY, self.DECIMAL_PRECISION))

        self.registerField('gravityInclude', self._ui.include)
        self.registerField('gravityX', self._ui.x)
        self.registerField('gravityY', self._ui.y)
        self.registerField('gravityZ', self._ui.z)

    def isComplete(self):
        complete = True

        for field in (self._x, self._y, self._z):
            if field.value() is None:
                complete = False
                break

        if complete != self._complete:
            self._complete = complete
            self.completeChanged.emit()

        return complete


