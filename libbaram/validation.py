#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from PySide6.QtCore import QCoreApplication


FLOAT_PATTERN = '[-+]?\d*\.?\d+([eE][-+]?\d+)?'

FLOAT_EXPRESSION = f'^{FLOAT_PATTERN}$'


class ValidationResult:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class FloatValidationResult(ValidationResult):
    def __init__(self, text):
        super().__init__(text)

    def float(self):
        return float(self._text)


def validateFloat(input: str, name: str,
                  low: Optional[float] = None, high: Optional[float] = None, lowInclusive=True, highInclusive=True):
    def rangeToText():
        if high is None:
            if lowInclusive:
                return f' (value ≥ {low})'
            else:
                return f' (value > {low})'

        lowText = ' ('
        if low is not None:
            if lowInclusive:
                lowText =  f' ({low} ≤ '
            else:
                lowText =  f' ({low} < '

        if highInclusive:
            return f'{lowText}value ≤ {high})'
        else:
            return f'{lowText}value < {high})'

    try:
        v = float(input)
    except ValueError as e:
        raise ValueError(f'{name} - {str(e)}')

    if low is not None:
        if v < low or (v == low and not lowInclusive):
            raise ValueError(f"{name} - {QCoreApplication.translate('Validation', 'Out of Range')}{rangeToText()}")
    if high is not None:
        if v > high or (v == high and not highInclusive):
            raise ValueError(f"{name} - {QCoreApplication.translate('Validation', 'Out of Range')}{rangeToText()}")

    return FloatValidationResult(input)
