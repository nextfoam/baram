#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox


class EnumComboBox(QComboBox):
    currentDataChanged = Signal(Enum)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._items = {}

        self.currentTextChanged.connect(self._currentDataChanged)

    def addItems(self, items):
        for enum, text in items.items():
            self._addItem(enum, text)

    def setCurrentData(self, enum):
        self.setCurrentText(self._items[enum])
        self._currentDataChanged()

    def isSelected(self, enum):
        return self.currentData() == enum

    def currentValue(self):
        return self.currentData().value

    def _addItem(self, enum, text):
        self.addItem(text, enum)
        self._items[enum] = text

    def _currentDataChanged(self):
        self.currentDataChanged.emit(self.currentData())
