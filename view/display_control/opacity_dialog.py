#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .opacity_dialog_ui import Ui_OpacityDialog


class OpacityDialog(QDialog):
    def __init__(self, parent, value):
        super().__init__(parent)
        self._ui = Ui_OpacityDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

        value = 100 if value is None else value * 100
        self._ui.slider.setValue(value)
        self._valueChanged(value)

    def value(self):
        return float(self._ui.value.text())

    def _connectSignalsSlots(self):
        self._ui.slider.valueChanged.connect(self._valueChanged)

    def _valueChanged(self, steps):
        self._ui.value.setText(str(steps / 100))
