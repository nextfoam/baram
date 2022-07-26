#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import Qt

from coredb import coredb
from .settings_language_ui import Ui_SettingLanguageDialog


class SettingLanguageDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self._ui = Ui_SettingLanguageDialog()
        self._ui.setupUi(self)

        # TODO: load current language from yaml config file
        language = self.tr("Korean")

        self._ui.language.setCurrentText(language)

    def accept(self):
        QMessageBox.information(self, self.tr("Change UI language"),
                                self.tr('Requires UI restart'))

        language = self._ui.language.currentText()

        # TODO: save selected language at yaml config file

        super().accept()
