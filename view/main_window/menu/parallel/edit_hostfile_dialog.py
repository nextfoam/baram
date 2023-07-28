#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QDialog, QFileDialog

from coredb.project import Project
from .edit_hostfile_dialog_ui import Ui_EditHostfileDialog


class EditHostfileDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_EditHostfileDialog()
        self._ui.setupUi(self)

        charFormat = self._ui.textEdit.currentCharFormat()
        fixedFont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        charFormat.setFont(fixedFont)
        self._ui.textEdit.setCurrentCharFormat(charFormat)

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.importButton.clicked.connect(self._selectHostfile)

    def accept(self):
        text = self._ui.textEdit.toPlainText()
        Project.instance().hostfile = text
        super().accept()

    def _load(self):
        self._ui.textEdit.setPlainText(Project.instance().hostfile)

    def _selectHostfile(self):
        self._dialog = QFileDialog(self, self.tr('Select hostfile'))
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._dialog.fileSelected.connect(self._hostfileSelected)
        self._dialog.open()

    def _hostfileSelected(self, file):
        with open(file, 'r') as f:
            self._ui.textEdit.insertPlainText(f.read())
