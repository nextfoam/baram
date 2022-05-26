#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog

from .multiphase_dialog_ui import Ui_MultiphaseDialog


class Model(Enum):
    OFF = auto()
    VOLUME_OF_FLUID = auto()
    MIXTURE = auto()


class MultiphaseModelDialog(QDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_MultiphaseDialog()
        self._ui.setupUi(self)

        self._ui.volumeOfFluid.hide()
        self._ui.mixture.hide()

        QTimer.singleShot(0, lambda: self.adjustSize())

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        pass
