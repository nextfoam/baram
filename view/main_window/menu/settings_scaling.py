#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from enum import Enum, auto

from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt

from coredb import coredb
from .settings_scaling_ui import Ui_SettingScalingDialog


class SettingScalingDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self._ui = Ui_SettingScalingDialog()
        self._ui.setupUi(self)

        # TODO: load current scaling from yaml config file

        scaling = '1.1'
        self._ui.scaling.setValue(float(scaling))

    def accept(self):
        scaling = str(self._ui.scaling.value())

        # TODO: save selected scaling at yaml config file

        super().accept()
