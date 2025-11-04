#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from baramFlow.base.base import Vector, BatchableNumber
from baramFlow.view.widgets.batchable_float_edit import BatchableFloatEdit


class VectorWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self._x = BatchableFloatEdit('0')
        self._y = BatchableFloatEdit('0')
        self._z = BatchableFloatEdit('0')

        layout = QHBoxLayout(self)
        layout.addWidget(QLabel('('))
        layout.addWidget(self._x)
        layout.addWidget(QLabel(','))
        layout.addWidget(self._y)
        layout.addWidget(QLabel(','))
        layout.addWidget(self._z)
        layout.addWidget(QLabel(')'))
        layout.setContentsMargins(0, 0, 0, 0)

    def setVector(self, vector):
        self._x.setBatchableNumber(vector.x)
        self._y.setBatchableNumber(vector.y)
        self._z.setBatchableNumber(vector.z)

    def vector(self):
        return Vector(BatchableNumber(self._x.text()), BatchableNumber(self._y.text()), BatchableNumber(self._z.text()))

    def validate(self, name: str):
        self._x.validate(f'{name}(X)')
        self._y.validate(f'{name}(Y)')
        self._z.validate(f'{name}(Z)')
