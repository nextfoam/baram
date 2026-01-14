#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys

from PySide6.QtWidgets import QApplication

from baramFlow.coredb.batch_parameter_db import BatchParametersDB


class PFloat():
    def __init__(self,
                 text: str,
                 name: str,
                 low:  float = -sys.float_info.max,
                 high: float =  sys.float_info.max,
                 lowInclusive:bool  = True,
                 highInclusive:bool = True):

        self._text = text.strip()

        if self._text.startswith('$'):  # Parametric value
            if len(self._text) < 2:
                raise ValueError(f"{name} - {QApplication.translate(b'PFloat', b'Invalid Parameter Name')}")

            try:
                value = float(BatchParametersDB.defaultValue(self._text[1:]))
            except LookupError:
                raise ValueError(f"{name} - {self.tr('Invalid User Parameter')}")

        else:
            try:
                value = float(self._text)
            except ValueError as e:
                raise ValueError(f'{name} - {str(e)}')

        if value < low:
            raise ValueError(f"{name} {QApplication.translate(b'PFloat', b'is less than ')} {low}")
        elif value == low and not lowInclusive:
            raise ValueError(f"{name} {QApplication.translate(b'PFloat', b'should be greater than ')} {low}")

        if value > high:
            raise ValueError(f"{name} {QApplication.translate(b'PFloat', b'is greater than ')} {high}")
        elif value == high and not highInclusive:
            raise ValueError(f"{name} {QApplication.translate(b'PFloat', b'should be less than ')} {high}")

        self._value = value

    def __str__(self):
        return self._text

    def __float__(self):
        return self._value

    def __gt__(self, other):
        if isinstance(other, PFloat):
            return self._value > other._value

        return self._value > other

    def __ge__(self, other):
        if isinstance(other, PFloat):
            return self._value >= other._value

        return self._value >= other

    def __lt__(self, other):
        if isinstance(other, PFloat):
            return self._value < other._value

        return self._value < other

    def __le__(self, other):
        if isinstance(other, PFloat):
            return self._value <= other._value

        return self._value <= other

