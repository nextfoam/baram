#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.base import BatchableNumber, Vector, Function1Scalar, Function1Vector
from baramFlow.base.constants import Function1Type
from baramFlow.coredb.coredb_reader import CoreDBReader


class DictionaryHelper:
    def __init__(self):
        self._parameters = CoreDBReader().parameters()

    def boolValue(self, value: bool):
        return 'true' if value else 'false'

    def pFloatValue(self, value: BatchableNumber):
        if value.isParameter():
            return self._parameters[value.parameter()]

        return value.text

    def vectorValue(self, value: Vector):
        return [self.pFloatValue(value.x), self.pFloatValue(value.y), self.pFloatValue(value.z)]

    def function1ScalarValue(self, value: Function1Scalar):
        if value.type == Function1Type.CONSTANT:
            return 'constant', self.pFloatValue(value.constant)
        elif value.type == Function1Type.TABLE:
            return 'table', [[[r.t], [r.v]] for r in value.table]

    def function1VectorValue(self, value: Function1Vector):
        if value.type == Function1Type.CONSTANT:
            return 'constant', self.vectorValue(value.constant)
        elif value.type == Function1Type.TABLE:
            return 'table', [[[r.t], [[r.x], [r.y], [r.z]]] for r in value.table]
