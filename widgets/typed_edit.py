#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator, QIntValidator
from PySide6.QtWidgets import QLineEdit


class FloatEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QDoubleValidator())


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

