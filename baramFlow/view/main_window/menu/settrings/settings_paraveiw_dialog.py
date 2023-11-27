#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import platform

from PySide6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox

from baramFlow.coredb.app_settings import AppSettings
from .settings_paraview_dialog_ui import Ui_ParaViewSettingDialog


class SettingsParaViewDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_ParaViewSettingDialog()
        self._ui.setupUi(self)

        if path := AppSettings.findParaviewInstalledPath():
            self._ui.filePath.setText(str(path))
        else:
            self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._connectSignalsSlots()

    def accept(self):
        AppSettings.updateParaviewInstalledPath(self._ui.filePath.text())

        super().accept()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._openFileDialog)

    def _openFileDialog(self):
        if platform.system() == 'Windows':
            self._dialog = QFileDialog(self, self.tr('Select ParaView Executable'), os.environ.get('PROGRAMFILES'), 'exe (*.exe)')
        else:
            self._dialog = QFileDialog(self, self.tr('Select ParaView Executable'))
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._dialog.fileSelected.connect(self._fileSelected)
        self._dialog.open()

    def _fileSelected(self, path):
        self._ui.filePath.setText(path)
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
