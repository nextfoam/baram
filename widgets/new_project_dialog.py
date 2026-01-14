#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox

from .new_project_widget import NewProjectWidget


class NewProjectDialog(QDialog):
    pathSelected = Signal(Path)

    def __init__(self, parent, title, path=None, suffix=None):
        super().__init__(parent)

        self.resize(500, self.size().height())

        self._widget = NewProjectWidget(self, path, suffix)

        layout = QVBoxLayout(self)
        layout.addWidget(self._widget)

        self._buttonBox = QDialogButtonBox(self)
        self._buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self._buttonBox)

        self.setWindowTitle(title)
        self._buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._connectSignalsSlots()

    def projectPath(self):
        return Path(self._widget.projectPath())

    def _connectSignalsSlots(self):
        self._widget.pathChanged.connect(self._pathChanged)
        self._buttonBox.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self._accept)
        self._buttonBox.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)

    def _pathChanged(self, path):
        self._buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(path is not None)

    def _accept(self):
        self.pathSelected.emit(self.projectPath())
        self.accept()
