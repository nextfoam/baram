#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from widgets.pfloat_line_edit import PFloatLineEdit

from baramFlow.base.base import Vector


class VectorWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self._x = PFloatLineEdit('0')
        self._y = PFloatLineEdit('0')
        self._z = PFloatLineEdit('0')

        layout = QHBoxLayout(self)
        layout.addWidget(QLabel('('))
        layout.addWidget(self._x)
        layout.addWidget(QLabel(','))
        layout.addWidget(self._y)
        layout.addWidget(QLabel(','))
        layout.addWidget(self._z)
        layout.addWidget(QLabel(')'))
        layout.setContentsMargins(0, 0, 0, 0)

    def setVector(self, vector: Vector):
        self._x.setPFloat(vector.x)
        self._y.setPFloat(vector.y)
        self._z.setPFloat(vector.z)

    def vector(self, name):
        return Vector(self._x.pFloat(name), self._y.pFloat(name), self._z.pFloat(name))
