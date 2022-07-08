#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage

from .multiphase_model_page_ui import Ui_MultiphaseModelPage


class MultiphaseModelPage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(MultiphaseModelPage, self).__init__(*args, **kwargs)

        self._ui = Ui_MultiphaseModelPage()
        self._ui.setupUi(self)

        self._ui.notInclude.setChecked(True)
        self.registerField('multiphaseModelsInclude', self._ui.include)

