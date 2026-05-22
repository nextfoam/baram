#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from app_properties import meshAppProperties

from .about_dialog_ui import Ui_AboutDialog
from .license_dialog import LicenseDialog


class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_AboutDialog()
        self._ui.setupUi(self)

        self._ui.logo.setPixmap(meshAppProperties.logo())
        self._ui.description.setText(self.tr(
            '<p><b><font size="4">{name} {version}</font></b></p>'
            '<p>Powered by open-source software</p>'
            '<p>Copyright &#169; 2026 nextfoam</p>').format(
                name=meshAppProperties.fullName,
                version=meshAppProperties.version))

        self._dialog = None

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.close.clicked.connect(self.close)
        self._ui.thirdPartySoftwares.clicked.connect(self._showLicenses)

    def _showLicenses(self):
        self._dialog = LicenseDialog(self)
        self._dialog.show()
