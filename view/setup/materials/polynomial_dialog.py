#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QWidget, QLineEdit, QHBoxLayout, QPushButton, QSizePolicy
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize

from .polynomial_dialog_ui import Ui_PolynomialDialog


class PolynomialDialog(QDialog):
    class ValueWidget(QWidget):
        def __init__(self, parent, index, value):
            super().__init__()
            self._setupUI()

            self._parent = parent
            self._index = index
            self.setValue(value)

            self._connectSignalsSlots()

        def setValue(self, value):
            self._value.setText(value)

        def value(self):
            return self._value.text()

        def _setupUI(self):
            self._layout = QHBoxLayout(self)
            self._layout.setContentsMargins(9, 0, 9, 0)

            self._value = QLineEdit(self)
            self._value.setEnabled(False)
            self._layout.addWidget(self._value)

            self._removeButton = QPushButton(self)
            sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            sizePolicy.setHeightForWidth(self._removeButton.sizePolicy().hasHeightForWidth())
            self._removeButton.setSizePolicy(sizePolicy)
            icon = QIcon()
            icon.addFile(u":/icons/close.svg", QSize(), QIcon.Normal, QIcon.Off)
            self._removeButton.setIcon(icon)

            self._layout.addWidget(self._removeButton)

        def _connectSignalsSlots(self):
            self._removeButton.clicked.connect(self._remove)

        def _remove(self):
            self._parent.removeAt(self._index)

    def __init__(self, title):
        super().__init__()
        self._ui = Ui_PolynomialDialog()
        self._ui.setupUi(self)
        self.setWindowTitle(title)

        self._valueWidgets = []

        self._setup()
        self._connectSignalsSlots()

    def values(self):
        values = []
        for widget in self._valueWidgets:
            values.append(widget.value())

        return values

    def removeAt(self, index):
        count = len(self._valueWidgets)
        for i in range(index, count - 1):
            self._valueWidgets[i].setValue(self._valueWidgets[i + 1].value())

        self._valueWidgets.pop()
        self._ui.formLayout.removeRow(count)
        self._ui.newNo.setText(str(count))

    def _setup(self):
        self._ui.newNo.setText("1")

    def _connectSignalsSlots(self):
        self._ui.newValue.textChanged.connect(self._newValueChanged)
        self._ui.add.clicked.connect(self._addValue)

    def _newValueChanged(self, text):
        self._ui.add.setEnabled(text != '')

    def _addValue(self):
        index = len(self._valueWidgets)
        widget = self.ValueWidget(self, index, self._ui.newValue.text())
        self._ui.formLayout.insertRow(index + 1, self._ui.newNo.text(), widget)
        self._valueWidgets.append(widget)

        self._ui.newNo.setText(str(index + 2))
        self._ui.newValue.clear()
        self._ui.newValue.setFocus()
