#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramFlow.coredb.app_settings import AppSettings
from .settings_scaling_dialog_ui import Ui_SettingScalingDialog


class SettingScalingDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_SettingScalingDialog()
        self._ui.setupUi(self)

        scaling = AppSettings.getUiScaling()
        self._ui.scaling.setValue(float(scaling))

    def accept(self):
        value = self._ui.scaling.value()
        scaling = str(f'{value:.1f}')

        preScaling = AppSettings.getUiScaling()
        if preScaling != scaling:
            QMessageBox.information(self, self.tr("Change UI language"), self.tr('Requires UI restart'))
            AppSettings.updateUiScaling(scaling)

        super().accept()
