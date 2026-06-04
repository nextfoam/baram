#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QLineEdit

from libbaram.pfloat import PFloat

FLOAT = r'^[-+]?\d*\.?\d+([eE][-+]?\d+)?$'

class FloatLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setValidator(QRegularExpressionValidator(QRegularExpression(FLOAT), self))

    def text(self):
        raise NotImplementedError

    def value(self, name='', *args, **kwargs):
        return str(PFloat(super().text(), name=name, *args, **kwargs))