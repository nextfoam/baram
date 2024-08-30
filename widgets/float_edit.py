#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QLineEdit


class FloatEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QDoubleValidator())
