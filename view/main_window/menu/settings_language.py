#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt

from coredb import coredb
from .settings_language_ui import Ui_SettingLanguageDialog


class SettingLanguageDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self._ui = Ui_SettingLanguageDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        # self._db.getValue('.//settings/ui/language')
        self._ui.language.setCurrentText(self.tr("Korean"))

    def accept(self):
        language = self._ui.language.currentText()
        # self._db.setValue('.//settings/ui/language', language)

        super().accept()

