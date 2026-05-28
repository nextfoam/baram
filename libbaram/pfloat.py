#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys

from PySide6.QtWidgets import QApplication

from baramFlow.coredb.libdb import E
from baramFlow.services.user_parameters import UserParameters


class PFloat():
    def __init__(self,
                 text: str,
                 name: str = '',
                 low:  float = -sys.float_info.max,
                 high: float =  sys.float_info.max,
                 lowInclusive:bool  = True,
                 highInclusive:bool = True):

        self._text = text.strip()

        if self._text.startswith('$'):  # Parametric value
            if len(self._text) < 2:
                raise ValueError(f"{name} - {QApplication.translate('PFloat', 'Invalid Parameter Name')}")

            try:
                resolvedText = UserParameters().getValue(self._text[1:])
                value = float(resolvedText)
            except LookupError:
                raise ValueError(f"{name} - {QApplication.translate('PFloat', 'Invalid User Parameter')}")

            self._isParam = True
            self._resolvedText = resolvedText

        else:
            try:
                value = float(self._text)
            except ValueError as e:
                raise ValueError(f'{name} - {str(e)}')

            self._isParam = False
            self._resolvedText = self._text

        if value < low:
            raise ValueError(f"{name} {QApplication.translate('PFloat', 'is less than ')} {low}")
        elif value == low and not lowInclusive:
            raise ValueError(f"{name} {QApplication.translate('PFloat', 'should be greater than ')} {low}")

        if value > high:
            raise ValueError(f"{name} {QApplication.translate('PFloat', 'is greater than ')} {high}")
        elif value == high and not highInclusive:
            raise ValueError(f"{name} {QApplication.translate('PFloat', 'should be less than ')} {high}")

        self._value = value

    @staticmethod
    def fromElement(e):
        # Round-trip the legacy ``batchParameter`` attribute. Older project files
        # encode parametric values as ``<tag batchParameter="NAME">resolvedValue</tag>``;
        # the element text holds a numeric default so the XSD (xs:double) stays valid.
        if parameter := e.get('batchParameter'):
            return PFloat('$' + parameter)
        return PFloat(e.text)

    def toElement(self, tag):
        # For parametric values write the resolved numeric value as element text and
        # the parameter name as ``batchParameter`` so the result validates as xs:double.
        # ``$NAME`` as raw text would fail XSD validation on the next project load.
        if self._isParam:
            return E(tag, self._resolvedText, batchParameter=self._text[1:])
        return E(tag, self._text)

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

