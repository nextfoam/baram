#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .settings_scaling_dialog_ui import  Ui_SettingScalingDialog


class SettingScalingDialog(QDialog):
    def __init__(self, parent, scale):
        super().__init__(parent)
        self._ui = Ui_SettingScalingDialog()
        self._ui.setupUi(self)

        self._scale = scale
        self._ui.scaling.setValue(float(scale))

    def scale(self):
        return self._scale

    def accept(self):
        value = self._ui.scaling.value()
        self._scale = str(f'{value:.1f}')

        super().accept()
