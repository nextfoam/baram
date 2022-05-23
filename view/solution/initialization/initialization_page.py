#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox

from .initialization_page_ui import Ui_InitializationPage
from .option_dialog import OptionDialog


class InitializationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_InitializationPage()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.create.clicked.connect(self._createOption)
        self._ui.delete_.clicked.connect(self._deleteOption)
        self._ui.display.clicked.connect(self._displayOption)
        self._ui.edit.clicked.connect(self._editOption)
        self._ui.selectSourceCase.clicked.connect(self._selectSourceCase)
        self._ui.initialize.clicked.connect(self._initialize)

    def load(self):
        pass

    def save(self):
        pass

    def _createOption(self):
        dialog = OptionDialog()
        dialog.exec()

    def _deleteOption(self):
        pass

    def _displayOption(self):
        pass

    def _editOption(self):
        dialog = OptionDialog()
        dialog.exec()

    def _selectSourceCase(self):
        directoryName = QFileDialog.getExistingDirectory(self, self.tr("Folder Selection"))

    def _initialize(self):
        confirm = QMessageBox.question(self, self.tr("Initialize"), self.tr("All saved data will be deleted. OK?"))
        if confirm == QMessageBox.Yes:
            pass
