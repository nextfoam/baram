#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv

from PySide6.QtWidgets import QDialog, QFileDialog, QWidget, QLineEdit, QPushButton, QLabel, QDialogButtonBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal

from .number_input_dialog_ui import Ui_NumberInputDialog


class PiecewiseLinearDialog(QDialog):
    class FieldWidget(QWidget):
        def __init__(self, fieldWidgets, buttonWidget):
            super().__init__()
            self._edits = fieldWidgets
            self._button = buttonWidget
            self._filled = False
            self._setupUI()

        def values(self):
            return [value.text() for value in self._edits]

        def clear(self):
            [value.clear() for value in self._edits]

        def setFocus(self):
            self._edits[0].setFocus()

        def _setupUI(self):
            self._layout = QHBoxLayout(self)
            self._layout.setContentsMargins(9, 0, 9, 0)

            [self._layout.addWidget(widget) for widget in self._edits]
            self._layout.addWidget(self._button)

    class EditFieldWidget(FieldWidget):
        removeClicked = Signal(int)
        changed = Signal(str)

        def __init__(self, index, columnCount):
            super().__init__([QLineEdit() for _ in range(columnCount)], QPushButton())

            self._index = index

            self._setup()
            self._connectSignalsSlots()

        def setValues(self, values):
            [self._edits[i].setText(values[i]) for i in range(len(self._edits))]

        def isFilled(self):
            return self._filled

        def _setup(self):
            self._button.setIcon(QIcon(u":/icons/close.svg"))

        def _connectSignalsSlots(self):
            [field.textChanged.connect(self._valueChanged) for field in self._edits]
            self._button.clicked.connect(self._remove)

        def _remove(self):
            self.removeClicked.emit(self._index)

        def _valueChanged(self, text):
            if text.strip() == "":
                self._filled = False
            elif not self._filled:
                for edit in self._edits:
                    if edit.text() == "":
                        return
                self._filled = True

            self.changed.emit(text)

    def __init__(self, title, columns, prefix=""):
        """Constructs a dialog for piecewise linear values.

        Args:
            title: The title of the dialog
            columns: List of column names
            prefix: The prefix of index
        """
        super().__init__()
        self._ui = Ui_NumberInputDialog()
        self._ui.setupUi(self)
        self.setWindowTitle(title)

        self._columnCount = len(columns)
        self._prefix = prefix
        self._no = 0
        self._rowFields = []

        self._scrollBar = self._ui.editArea.verticalScrollBar()
        self._scrollBar.rangeChanged.connect(lambda: self._scrollBar.setValue(self._scrollBar.maximum()))
        self._setup(columns)
        self._connectSignalsSlots()

    def clear(self):
        while self._layout.rowCount() > 1:
            self._layout.removeRow(1)
        self._no = 0
        self._rowFields = []

    def _setup(self, columns):
        headers = []
        for column in columns:
            header = QLabel(column)
            header.setAlignment(Qt.AlignCenter)
            headers.append(header)
        emptyButton = QLabel()
        emptyButton.setFixedSize(28, 24)

        self._layout = self._ui.polynomialWidget.layout()
        self._layout.addRow("", self.FieldWidget(headers, emptyButton))
        self._ui.editArea.setMinimumWidth(self._columnCount * 80 + 100)
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._addFocusedRow)
        self._ui.file.clicked.connect(self._loadFile)

    def _addRow(self):
        label = self._prefix + str(self._no)
        row = self.EditFieldWidget(len(self._rowFields), self._columnCount)
        self._layout.addRow(label, row)
        self._rowFields.append(row)
        self._no = self._no + 1

        row.removeClicked.connect(self._removeAt)
        row.changed.connect(self._valueChanged)

        return row

    def _addFocusedRow(self):
        row = self._addRow()
        row.setFocus()
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    def _loadFile(self):
        fileName = QFileDialog.getOpenFileName(self, self.tr("Open CSV File"), "", self.tr("CSV (*.csv)"))
        if fileName[0]:
            with open(fileName[0]) as file:
                self.clear()
                reader = csv.reader(file)
                for line in reader:
                    for i in range(len(line), self._columnCount):
                        line.append('')
                    row = self._addRow()
                    row.setValues(line)

    def _removeAt(self, index):
        count = len(self._rowFields)
        for i in range(index, count - 1):
            self._rowFields[i].setValues(self._rowFields[i + 1].values())

        self._rowFields.pop()
        self._layout.removeRow(count)
        self._no = self._no - 1

        if index == count - 1:
            self._updateSubmitEnabled()

    def _valueChanged(self, text):
        if text.strip() == "":
            self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        else:
            self._updateSubmitEnabled()

    def _updateSubmitEnabled(self):
        for field in self._rowFields:
            if not field.isFilled():
                self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
                return
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)


class PolynomialDialog(PiecewiseLinearDialog):
    def __init__(self, title, prefix=""):
        """Constructs a dialog for polynomial coefficients.

        Args:
            title: The title of the dialog
            prefix: The prefix of index
        """
        super().__init__(title, [self.tr("Coefficient")], prefix)
        self._ui.file.hide()
