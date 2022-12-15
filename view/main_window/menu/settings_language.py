#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import QLocale

from coredb.app_settings import AppSettings
from .settings_language_ui import Ui_SettingLanguageDialog


languages = [
    [  # ISO 639-1 Two-Letter codes
        'de', 'en', 'es', 'fi', 'fr',
        'it', 'ja', 'ko', 'nl', 'pl',
        'pt', 'ru', 'sv', 'tr', 'zh'
    ],
    [  # Display String for each language
        'Deutsch', 'English', 'Español', 'Suomi', 'Français',
        'Italiano', '日本語', '한국어', 'Nederlands', 'Polski',
        'Português', 'русском', 'Svenska', 'Türkçe', '简体中文'
    ]
]

class SettingLanguageDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_SettingLanguageDialog()
        self._ui.setupUi(self)

        self._ui.language.addItems(languages[1])
        index = languages[0].index(QLocale.languageToCode(AppSettings.getLocale().language()))
        self._ui.language.setCurrentIndex(index)

    def accept(self):
        index = self._ui.language.currentIndex()

        preIndex = languages[0].index(QLocale.languageToCode(AppSettings.getLocale().language()))
        if preIndex != index:
            QMessageBox.information(self, self.tr("Change Locale"), self.tr('Locale change will be effective from next start'))
            AppSettings.setLocale(QLocale(languages[0][index]))

        super().accept()
