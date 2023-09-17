#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from baramSnappy.app import app
from .about_dialog_ui import Ui_AboutDialog
from .license_dialog import LicenseDialog


VERSION = '23.0.0'


class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_AboutDialog()
        self._ui.setupUi(self)

        self._ui.logo.setPixmap(app.properties.logo())

        self._dialog = None

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.close.clicked.connect(self.close)
        self._ui.thirdPartySoftwares.clicked.connect(self._showLicenses)

    def _showLicenses(self):
        self._dialog = LicenseDialog(self)
        self._dialog.show()
