#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QDialog, QFileDialog

from baramFlow.coredb import coredb
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

    def accept(self):
        text = self._ui.textEdit.toPlainText()
        # data = text.encode('utf-8')
        # db.setValue('.//parallel/hostfile', base64.b64encode(data))
        db = coredb.CoreDB()
        db.setValue('.//parallel/hostfile', text)
        super().accept()

    def _connectSignalsSlots(self):
        self._ui.importButton.clicked.connect(self._selectHostfile)

    def _load(self):
        # data = base64.b64decode(db.getValue('.//parallel/hostfile'))
        # self._ui.textEdit.setPlainText(data.decode('utf-8'))
        db = coredb.CoreDB()
        self._ui.textEdit.setPlainText(db.getValue('.//parallel/hostfile'))

    def _selectHostfile(self):
        self._dialog = QFileDialog(self, self.tr('Select hostfile'))
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._dialog.fileSelected.connect(self._hostfileSelected)
        self._dialog.open()

    def _hostfileSelected(self, file):
        with open(file, 'r') as f:
            self._ui.textEdit.insertPlainText(f.read())
