#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.base import Vector, Function1Scalar, Function1Vector
from baramFlow.base.constants import Function1Type
from baramFlow.coredb.coredb_reader import CoreDBReader


class DictionaryHelper:
    def __init__(self):
        self._parameters = CoreDBReader().parameters()

    def boolValue(self, value: bool):
        return 'true' if value else 'false'

    def vectorValue(self, value: Vector):
        return [float(value.x), float(value.y), float(value.z)]

    def function1ScalarValue(self, value: Function1Scalar):
        if value.type == Function1Type.CONSTANT:
            return 'constant', float(value.constant)
        elif value.type == Function1Type.TABLE:
            return 'table', [[[r.t], [r.v]] for r in value.table]

    def function1VectorValue(self, value: Function1Vector):
        if value.type == Function1Type.CONSTANT:
            return 'constant', self.vectorValue(value.constant)
        elif value.type == Function1Type.TABLE:
            return 'table', [[[r.t], [[r.x], [r.y], [r.z]]] for r in value.table]
