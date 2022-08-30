#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb.app_settings import AppSettings
from .settings_language_ui import Ui_SettingLanguageDialog


languages = [
    ['lang_de', 'lang_en', 'lang_es', 'lang_fr', 'lang_it',
     'lang_ja', 'lang_ko', 'lang_nl', 'lang_pl', 'lang_pt',
     'lang_ru', 'lang_sv', 'lang_tr', 'lang_zh'
     ],
    ['Deutsch', 'English', 'Español', 'Français', 'Italiano',
     '日本語', '한국어', 'Nederlands', 'Polski', 'Português',
     'русском', 'Svenska', 'Türkçe', '简体中文'
     ]
]

class SettingLanguageDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self._ui = Ui_SettingLanguageDialog()
        self._ui.setupUi(self)

        self._ui.language.addItems(languages[1])
        index = languages[0].index(AppSettings.getDefaultLanguage())
        self._ui.language.setCurrentIndex(index)

    def accept(self):
        index = self._ui.language.currentIndex()

        preIndex = languages[0].index(AppSettings.getDefaultLanguage())
        if preIndex != index:
            QMessageBox.information(self, self.tr("Change UI language"), self.tr('Requires UI restart'))
            AppSettings.updateDefaultLanguage(languages[0][index])

        super().accept()
