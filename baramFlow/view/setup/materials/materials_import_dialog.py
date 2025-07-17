#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox

from .materials_import_dialog_ui import Ui_MaterialsImportDialog


class MaterialsImportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MaterialsImportDialog()
        self._ui.setupUi(self)

        self._dialog = None

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._connectSignalsSlots()

    def isClearChecked(self):
        return self._ui.overwrite.isChecked()

    def selectedFile(self):
        return self._ui.file.text()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._openFileSelectorDialog)

    def _openFileSelectorDialog(self):
        self._dialog = QFileDialog(self, self.tr('Import Batch Parameters'), '', self.tr('CSV (*.csv)'))
        self._dialog.fileSelected.connect(self._fileSelected)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _fileSelected(self, file):
        self._ui.file.setText(file)
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
