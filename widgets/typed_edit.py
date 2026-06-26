#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from libbaram.validation import validateFloat

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator, QIntValidator
from PySide6.QtWidgets import QLineEdit


class FloatEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QDoubleValidator())

    def validate(self, name: str, low: Optional[float] = None,
                 high: Optional[float] = None, lowInclusive=True, highInclusive=True):
        return validateFloat(self.text(), name, low, high, lowInclusive, highInclusive)


class IdentifierEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z][A-Za-z0-9_\.]*')))


class MonitorNameEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_\-\.]*')))


class IntEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QIntValidator())

        self._name: str = ''
        self._low: int | None = None
        self._high: int | None = None
        self._lowInclusive: bool = True
        self._highInclusive: bool = True

    def setValidationRule(self, name: str = '',
                          low: int = None, high: int = None, lowInclusive:bool  = True, highInclusive:bool = True):
        self._name = name
        self._low = low
        self._high = high
        self._lowInclusive = lowInclusive
        self._highInclusive = highInclusive

    def text(self):
        value = int(super().text())

        if self._low is not None:
            if value < self._low:
                raise ValueError(self.tr('{0} is less than {1}.').format(self._name, self._low))
            elif value == self._low and not self._lowInclusive:
                raise ValueError(self.tr('{0} should be greater than {1}.').format(self._name, self._low))

        if self._high is not None:
            if value > self._high:
                raise ValueError(self.tr('{0} is greater than {1}.').format(self._name, self._high))
            elif value == self._high and not self._highInclusive:
                raise ValueError(self.tr('{0} should be less than {1}').format(self._name, self._high))

        return super().text()
