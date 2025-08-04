#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv

from PySide6.QtWidgets import QDialog, QFileDialog, QWidget, QLineEdit, QPushButton, QLabel, QDialogButtonBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal

from .number_input_dialog_ui import Ui_NumberInputDialog


class PiecewiseLinearDialog(QDialog):
    class RowWidget(QWidget):
        def __init__(self, fieldWidgets, buttonWidget):
            super().__init__()
            self._edits = fieldWidgets
            self._button = buttonWidget
            self._filled = False
            self._setupUI()

        def value(self, index):
            return self._edits[index].text().strip()

        def values(self):
            return [value.text() for value in self._edits]

        def clear(self):
            for value in self._edits:
                value.clear()

        def setFocus(self):
            self._edits[0].setFocus()

        def _setupUI(self):
            self._layout = QHBoxLayout(self)
            self._layout.setContentsMargins(9, 0, 9, 0)

            for widget in self._edits:
                self._layout.addWidget(widget)
            self._layout.addWidget(self._button)

    class EditRowWidget(RowWidget):
        removeClicked = Signal(int)
        changed = Signal(str)

        def __init__(self, index, columnCount):
            super().__init__([QLineEdit() for _ in range(columnCount)], QPushButton())

            self._index = index
            self._button.setIcon(QIcon(u":/icons/close.svg"))

            self._connectSignalsSlots()

        def setValues(self, values):
            for i in range(len(self._edits)):
                self._edits[i].setText(values[i])

        def isFilled(self):
            return self._filled

        def _connectSignalsSlots(self):
            for field in self._edits:
                field.textChanged.connect(self._valueChanged)
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

    def __init__(self, parent, title, columns, data, prefix="", maxRows=0):
        """Constructs a dialog for piecewise linear values.

        Args:
            title: The title of the dialog
            columns: List of column names
            data: list of space-separated column data
                ["column1_value1 column1_value2, ...", "column2_value1 column2_value2, ...", ...]
            prefix: The prefix of index
        """
        super().__init__(parent)
        self._ui = Ui_NumberInputDialog()
        self._ui.setupUi(self)
        self.setWindowTitle(title)

        self._columnCount = len(columns)
        self._prefix = prefix
        self._no = 0
        self._rowFields = []

        self._maxRows = maxRows

        self._dialog = None

        self._scrollBar = self._ui.editArea.verticalScrollBar()
        self._scrollBar.rangeChanged.connect(lambda: self._scrollBar.setValue(self._scrollBar.maximum()))

        self._connectSignalsSlots()

        self._setColumns(columns)
        self._setData(data)

    def clear(self):
        while self._layout.rowCount() > 1:
            self._layout.removeRow(1)
        self._no = 0
        self._rowFields = []

    def getValues(self):
        values = []
        for i in range(self._columnCount):
            joinedValues = ''
            for field in self._rowFields:
                joinedValues = joinedValues + field.value(i) + ' '
            values.append(joinedValues[:-1])

        return values

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._addFocusedRow)
        self._ui.file.clicked.connect(self._loadFile)

    def _setColumns(self, columns):
        headers = []
        for column in columns:
            header = QLabel(column)
            header.setAlignment(Qt.AlignCenter)
            headers.append(header)
        emptyButton = QLabel()
        emptyButton.setFixedSize(28, 24)

        self._layout = self._ui.polynomialWidget.layout()
        self._layout.addRow("", self.RowWidget(headers, emptyButton))
        self._ui.editArea.setMinimumWidth(self._columnCount * 80 + 100)
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _setData(self, data):
        values = [d.split() if d else [] for d in data]

        for i in range(len(values[0])):
            row = self._addRow()
            row.setValues([v[i] for v in values])

    def _addRow(self):
        label = self._prefix + str(self._no)
        row = self.EditRowWidget(len(self._rowFields), self._columnCount)
        self._layout.addRow(label, row)
        self._rowFields.append(row)
        self._no = self._no + 1

        row.removeClicked.connect(self._removeAt)
        row.changed.connect(self._valueChanged)

        if self._no >= self._maxRows > 0:
            self._ui.add.setEnabled(False)

        return row

    def _addFocusedRow(self):
        row = self._addRow()
        row.setFocus()
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _loadFile(self):
        self._dialog = QFileDialog(self, self.tr('Select CSV File'), '', 'CSV (*.csv)')
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._dialog.accepted.connect(self._fileSelected)
        self._dialog.open()

    def _removeAt(self, index):
        count = len(self._rowFields)
        for i in range(index, count - 1):
            self._rowFields[i].setValues(self._rowFields[i + 1].values())

        self._rowFields.pop()
        self._layout.removeRow(count)
        self._no = self._no - 1

        self._ui.add.setEnabled(True)
        self._updateSubmitEnabled()

    def _valueChanged(self, text):
        if text.strip() == "":
            self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        else:
            self._updateSubmitEnabled()

    def _updateSubmitEnabled(self):
        if len(self._rowFields) == 0:
            self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return

        for field in self._rowFields:
            if not field.isFilled():
                self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
                return

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def _fileSelected(self):
        if files := self._dialog.selectedFiles():
            with open(files[0]) as file:
                self.clear()
                reader = csv.reader(file)
                for line in reader:
                    for i in range(len(line), self._columnCount):
                        line.append('')
                    row = self._addRow()
                    row.setValues(line)


class PolynomialDialog(PiecewiseLinearDialog):
    def __init__(self, parent, title, data, prefix=""):
        """Constructs a dialog for polynomial coefficients.

        Args:
            title: The title of the dialog
            data: Space-separated column data. "value1 value2 ..."
            prefix: The prefix of index
        """
        super().__init__(parent, title, [self.tr("Coefficient")], [data], prefix, 8)
        self._ui.file.hide()

        self.resize(self.size().width(), 382)

    def getValues(self):
        values = ''
        for field in self._rowFields:
            values = values + field.value(0) + ' '

        return values[:-1]

    def resizeEvent(self, arg__1):
        print(self.size())
