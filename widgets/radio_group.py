#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal


class RadioGroup(QObject):
    valueChanged = Signal(str)

    def __init__(self, radioGroup):
        super().__init__()

        self._group = radioGroup
        self._values = {}
        self._buttons = {}

        self._connectSignalsSlots()

    def setObjectMap(self, map, currentValue=None):
        for radio in self._group.buttons():
            self._values[self._group.id(radio)] = map[radio.objectName()]
            self._buttons[map[radio.objectName()]] = radio
            if currentValue == map[radio.objectName()]:
                radio.setChecked(True)

        self.valueChanged.emit(currentValue)

    def value(self):
        return self._values[self._group.checkedId()]

    def setValue(self, value):
        self._buttons[value].setChecked(True)

    def _connectSignalsSlots(self):
        self._group.buttonClicked.connect(self._radioClicked)

    def _radioClicked(self):
        self.valueChanged.emit(self.value())
