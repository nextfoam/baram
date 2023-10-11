#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QButtonGroup


class EnumButtonGroup(QObject):
    valueChecked = Signal(Enum)

    def __init__(self):
        super().__init__()

        self._group = QButtonGroup()
        self._buttons = []

        self._group.idClicked.connect(self._idClicked)

    def addButton(self, button, enum):
        self._group.addButton(button, len(self._buttons))
        self._buttons.append(enum)

    def setCheckedButton(self, enum):
        id_ = self._buttons.index(enum)
        self._group.button(id_).setChecked(True)
        self._idClicked(id_)

    def _idClicked(self, id_):
        self.valueChecked.emit(self._buttons[id_].value)
