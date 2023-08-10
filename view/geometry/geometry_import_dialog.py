#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QListWidgetItem

from .geometry_import_dialog_ui import Ui_ImportDialog


class ImportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ImportDialog()
        self._ui.setupUi(self)

        self._dialog = None

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._connectSignalsSlots()

    def files(self):
        return [Path(self._ui.files.item(i).text()) for i in range(self._ui.files.count())]

    def featureAngle(self):
        return self._ui.featureAngle.text() if self._ui.splitSurface.isChecked() else None

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._openFileDialog)

    def _openFileDialog(self):
        self._dialog = QFileDialog(self, self.tr('Select STL File'), '', 'STL (*.stl)')
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self._dialog.filesSelected.connect(self._filesSelected)
        self._dialog.open()

    def _filesSelected(self, files):
        self._ui.files.clear()
        for f in files:
            self._ui.files.addItem(QListWidgetItem(f))

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
