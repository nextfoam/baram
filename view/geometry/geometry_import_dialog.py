#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog

from .geometry_import_dialog_ui import Ui_ImportDialog


class ImportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ImportDialog()
        self._ui.setupUi(self)

        self._dialog = None

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._connectSignalsSlots()

    def filePath(self):
        return Path(self._ui.file.text())

    def featureAngle(self):
        return self._ui.featureAngle.text() if self._ui.splitSurface.isChecked() else None

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._openFileDialog)

    def _openFileDialog(self):
        self._addDialog = QFileDialog(self, self.tr('Select STL File'), '', 'STL (*.stl)')
        self._addDialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._addDialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self._addDialog.fileSelected.connect(self._fileSelected)
        self._addDialog.open()

    def _fileSelected(self, file):
        self._ui.file.setText(file)
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
