#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QDialog, QMessageBox

from baramFlow.app import app
from baramFlow.base import expert_mode

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
        self._position = 0
        self._sequence = "ilovebaram".upper()

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.close.clicked.connect(self.close)
        self._ui.thirdPartySoftwares.clicked.connect(self._showLicenses)

    def _showLicenses(self):
        self._dialog = LicenseDialog(self)
        self._dialog.show()

    def keyPressEvent(self, event: QKeyEvent):
        try:
            char = chr(event.key())
        except ValueError:
            char = ''

        # Check if this character continues the expected sequence
        if self._position < len(self._sequence) and char == self._sequence[self._position]:
            self._position += 1

            if self._position == len(self._sequence):
                self._expertModeRequested()
                self._position = 0
        else:
            # Reset and check if this char starts the sequence
            if char == self._sequence[0]:
                self._position = 1
            else:
                self._position = 0

        super().keyPressEvent(event)

    def _expertModeRequested(self):
        if not expert_mode.isExpertModeActivated():
            expert_mode.activateExpertMode()

            QMessageBox.information(
                self,
                self.tr('Expert mode'),
                self.tr(f'Expert mode activated!'))
