#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from baramMesh.app import app
from .language_dialog_ui import Ui_LanguageDialog


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


class LanugageDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_LanguageDialog()
        self._ui.setupUi(self)

        for i in range(len(languages[1])):
            self._ui.language.addItem(languages[1][i], languages[0][i])

        self._ui.language.setCurrentIndex(languages[0].index(app.settings.getLanguage()))

    def accept(self):
        language = self._ui.language.currentData()
        if app.settings.setLanguage(language):
            app.applyLanguage()

        super().accept()
