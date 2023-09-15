#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from baram.app import app
from baram.coredb.app_settings import AppSettings
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

        language = AppSettings.getLanguage()
        for i in range(len(languages[1])):
            self._ui.language.addItem(languages[1][i], languages[0][i])
            if language == languages[0][i]:
                self._ui.language.setCurrentIndex(i)

    def accept(self):
        language = self._ui.language.currentData()

        if language != AppSettings.getLanguage():
            AppSettings.setLanguage(language)
            app.setLanguage(language)

        super().accept()
