#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup


class EnumButtonGroup(QButtonGroup):
    dataChecked = Signal(Enum)

    def __init__(self):
        super().__init__()

        self._buttons = []

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self.idToggled.connect(self._idToggled)

    def addEnumButton(self, button, enum):
        self.addButton(button, len(self._buttons))
        self._buttons.append(enum)

    def setCheckedData(self, enum):
        self.button(self._buttons.index(enum)).setChecked(True)

    def checkedData(self):
        return self._buttons[self.checkedId()]

    def _idToggled(self, id_, checked):
        if checked:
            self.dataChecked.emit(self._buttons[id_])
