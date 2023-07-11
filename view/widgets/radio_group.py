#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal


class RadioGroup(QObject):
    valueChanged = Signal(str)

    def __init__(self, radioGroup):
        super().__init__()

        self._group = radioGroup
        self._values = {}

        self._connectSignalsSlots()

    def setObjectMap(self, map, currentValue=None):
        for radio in self._group.buttons():
            self._values[self._group.id(radio)] = map[radio.objectName()]
            if currentValue == map[radio.objectName()]:
                radio.setChecked(True)

    def value(self):
        return self._values[self._group.checkedId()]

    def _connectSignalsSlots(self):
        self._group.buttonClicked.connect(self._radioClicked)

    def _radioClicked(self):
        self.valueChanged.emit(self.value())
