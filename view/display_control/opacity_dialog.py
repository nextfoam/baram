#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .opacity_dialog_ui import Ui_OpacityDialog


class OpacityDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_OpacityDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def opacity(self):
        return int(self._ui.value.text()) / 100

    def setOpacity(self, opacity):
        grade = 10 if opacity is None else int(opacity * 10)
        self._ui.slider.setValue(grade)
        self._valueChanged(grade)

    def _connectSignalsSlots(self):
        self._ui.slider.valueChanged.connect(self._valueChanged)

    def _valueChanged(self, grade):
        self._ui.value.setText(str(grade * 10))
