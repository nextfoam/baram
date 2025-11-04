#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from baramFlow.base.base import BatchableNumber
from libbaram.validation import validateFloat, FLOAT_EXPRESSION

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QLineEdit

from baramFlow.coredb.batch_parameter_db import BATCH_ARGUMENT_PATTERN, BatchParametersDB


class BatchableFloatEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._validated = False
        self._batchParameter = False
        self._batchDefault = None

        self.setValidator(QRegularExpressionValidator(
            QRegularExpression(F'({FLOAT_EXPRESSION})|({BATCH_ARGUMENT_PATTERN})')))

        self.editingFinished.connect(self._clearValidation)

    def validate(self, name: str, low: Optional[float] = None,
                 high: Optional[float] = None, lowInclusive=True, highInclusive=True):
        text = self.text().strip()
        if text.startswith('$'):
            if len(text) < 2:
                raise ValueError(f"{name} - {self.tr('Invalid Batch Parameter')}")

            try:
                value = BatchParametersDB.defaultValue(text[1:])
                validateFloat(value, name, low, high, lowInclusive, highInclusive)
            except LookupError:
                raise ValueError(f"{name} - {self.tr('Invalid Batch Parameter')}")
            except ValueError as e:
                raise ValueError(f"{self.tr('Invalid default value has been assigned to the batch parameter.')}\n({str(e)})")

            self._batchParameter = True
            self._batchDefault = value
        else:
            validateFloat(text, name, low, high, lowInclusive, highInclusive)

        self._validated = True

    def validatedFloat(self):
        assert self._validated
        return float(self._batchDefault) if self._batchParameter else float(self.text())

    def batchableNumber(self):
        return BatchableNumber(self.text(), self._batchDefault)

    def setBatchableNumber(self, number: BatchableNumber):
        self.setText(number.text)

    def _clearValidation(self):
        self._validate = False
