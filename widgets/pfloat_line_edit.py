#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QLineEdit

from libbaram.pfloat import PFloat

FLOAT = r'^[-+]?\d*\.?\d+([eE][-+]?\d+)?$'
PARAMETER = r'^\$[A-Z_][A-Z0-9_]*$'

class PFloatLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setValidator(QRegularExpressionValidator(QRegularExpression(F'({FLOAT})|({PARAMETER})'), self))

    def setPFloat(self, value: PFloat):
        self.setText(str(value))

    def pFloat(self, name='', *args, **kwargs):
        return PFloat(self.text(), name=name, *args, **kwargs)