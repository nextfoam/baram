#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QDialog

from libbaram.pfloat import PFloat
from widgets.pfloat_line_edit import PFloatLineEdit
from widgets.python_combo_box import PythonComboBox

from baramFlow.base.base import Function1VectorRow, Function1ScalarRow, Function1Data, Vector
from baramFlow.base.constants import Function1Type
from baramFlow.view.widgets.piecewise_linear_dialog import PiecewiseLinearDialog
from baramFlow.view.widgets.vector_widget import VectorWidget


class EditButtonWidget(QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()

        self._button = QPushButton(self.tr('Show/Edit'))

        self._data = None

        layout = QHBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self._button)
        layout.setContentsMargins(0, 0, 0, 0)

        self._button.clicked.connect(self.clicked)

    def setData(self, data):
        self._data = data

    def data(self):
        return self._data


class Function1Widget(QWidget):
    tableEditButtonClicked = Signal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self._layout = QHBoxLayout(self)
        self._type = PythonComboBox(self)

        self._inputs: dict[Function1Type, PFloatLineEdit | VectorWidget | EditButtonWidget] = {}
        self._data: Function1Data

        self._dialog: QDialog

        self._typeTexts = {
            Function1Type.CONSTANT: 'Constant',
            Function1Type.TABLE:    'Table'
        }

        self._layout.addWidget(self._type)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._connectSignalsSlots()

    def setup(self, types: list[Function1Type]):
        for t in types:
            self._type.addItem(self._typeTexts[t], t)

            if t == Function1Type.CONSTANT:
                self._inputs[t] = self._createConstantWidget()
            elif t == Function1Type.TABLE:
                self._inputs[t] = EditButtonWidget()
                self._inputs[t].clicked.connect(self._openTableEditDialog)

            self._layout.addWidget(self._inputs[t])
            self._inputs[t].hide()

        self._typeChanged()

    def setData(self, data: Function1Data):
        self._data = data

        if data.type in self._inputs:
            self._type.setCurrentIndex(self._type.findData(data.type))
        else:
            self._type.setCurrentIndex(0)

        if data.constant is not None:
            self._setConstantData(data.constant)

        if Function1Type.TABLE in self._inputs:
            self._inputs[Function1Type.TABLE].setData([] if data.table is None else data.table)

    def data(self, name: str, *args, **kwargs):
        data = copy.deepcopy(self._data)
        data.type = self._type.currentData()

        if data.type == Function1Type.CONSTANT:
            data.constant = self._constantData(name=name, *args, **kwargs)
        elif data.type == Function1Type.TABLE:
            data.table = self._inputs[data.type].data()
            if not data.table:
                raise ValueError('Edit {0}.'.format(name))

        return data

    def _connectSignalsSlots(self):
        self._type.currentIndexChanged.connect(self._typeChanged)

    def _typeChanged(self):
        for t, input in self._inputs.items():
            input.setVisible(t == self._type.currentData())

    def _setConstantData(self, value):
        raise NotImplementedError

    def _constantData(self, name: str, *args, **kwargs):
        raise NotImplementedError

    def _createConstantWidget(self):
        raise NotImplementedError

    def _openTableEditDialog(self):
        raise NotImplementedError


class Function1ScalarWidget(Function1Widget):
    def _setConstantData(self, value: PFloat):
        self._inputs[Function1Type.CONSTANT].setPFloat(value)

    def _constantData(self, name: str, *args, **kwargs):
        return self._inputs[Function1Type.CONSTANT].pFloat(name=name, *args, **kwargs)

    def _createConstantWidget(self):
        return PFloatLineEdit(self)

    def _openTableEditDialog(self):
        self._dialog = PiecewiseLinearDialog(
            self, self.tr('Table'), 't', '', ['v'], '',
            [[float(row.t), float(row.v)] for row in self._inputs[Function1Type.TABLE].data()])
        self._dialog.accepted.connect(self._updateTable)
        self._dialog.open()

    def _updateTable(self):
        self._inputs[Function1Type.TABLE].setData(
            [Function1ScalarRow(*[str(v) for v in row]) for row in self._dialog.getData()])


class Function1VectorWidget(Function1Widget):
    def _setConstantData(self, value: Vector):
        self._inputs[Function1Type.CONSTANT].setVector(value)

    def _constantData(self, name: str):
        return self._inputs[Function1Type.CONSTANT].vector(name)

    def _createConstantWidget(self):
        return VectorWidget(self)

    def _openTableEditDialog(self):
        self._dialog = PiecewiseLinearDialog(
            self, self.tr('Table'), 't', '', ['x', 'y', 'z'], '',
            [[float(row.t), float(row.x), float(row.y), float(row.z)] for row in self._inputs[Function1Type.TABLE].data()])
        self._dialog.accepted.connect(self._updateTable)
        self._dialog.open()

    def _updateTable(self):
        self._inputs[Function1Type.TABLE].setData([Function1VectorRow(*row) for row in self._dialog.getData()])
