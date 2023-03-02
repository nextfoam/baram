#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal


class EnumComboBox(QObject):
    currentValueChanged = Signal(str)

    def __init__(self, comboBox):
        super().__init__()

        self._comboBox = comboBox
        self._items = {}

        self._comboBox.currentTextChanged.connect(self._currentIndexChanged)

    def addItem(self, enum, text):
        self._comboBox.addItem(text, enum.value)
        self._items[enum.value] = text

    def setCurrentValue(self, value):
        self._comboBox.setCurrentText(self._items[value])
        self._currentIndexChanged()

    def currentValue(self):
        return self._comboBox.currentData()

    def isSelected(self, enum):
        return enum.value == self._comboBox.currentData()

    def _currentIndexChanged(self):
        self.currentValueChanged.emit(self._comboBox.currentData())
