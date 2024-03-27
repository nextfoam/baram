#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage

from .last_page_ui import Ui_LastPage


class LastPage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(LastPage, self).__init__(*args, **kwargs)

        self._ui = Ui_LastPage()
        self._ui.setupUi(self)

