#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from pathlib import Path

from PySide6.QtCore import QRegularExpression, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QFileDialog, QWidget

from .new_project_widget_ui import Ui_NewProjectWidget


class NewProjectWidget(QWidget):
    pathChanged = Signal(Path)

    def __init__(self, parent, path: Path = None, suffix=None):
        super().__init__(parent)

        self._ui = Ui_NewProjectWidget()
        self._ui.setupUi(self)

        self._suffix = ''

        self._validatedPath = None

        self._dialog = None

        self._ui.projectName.setValidator(
            QRegularExpressionValidator(QRegularExpression('[^\s\\\\/:*?"<>|][^\\\\/:*?"<>|]*')))

        location = str(path.resolve() if path and path.exists() else Path.home())
        self._ui.projectLocation.setText(location)

        self._ui.locationDescription.setText(self._ui.locationDescription.text() + os.sep)

        self._connectSignalsSlots()

        if suffix is None:
            self._ui.formLayout.removeRow(self._ui.suffixField)
        else:
            self._ui.suffix.addItem(suffix, suffix)
            self._ui.suffix.addItem(self.tr('<no suffix>'), '')

    def projectPath(self):
        return self._validatedPath

    def validationMessage(self):
        return self._ui.validationMessage.text()

    def setFixedProjectPath(self, path):
        self._ui.projectName.setText(path.name)
        self._ui.projectLocation.setText(str(path.parent.resolve()))
        self._ui.validationMessage.hide()
        self.setEnabled(False)

    def hideValidationMessage(self):
        self._ui.validationMessage.hide()

    def _connectSignalsSlots(self):
        self._ui.projectName.textChanged.connect(self._updateProjectPath)
        self._ui.suffix.currentIndexChanged.connect(self._suffixChanged)
        self._ui.select.clicked.connect(self._selectLocation)

    def _suffixChanged(self):
        self._suffix = self._ui.suffix.currentData()
        self._updateProjectPath()

    def _selectLocation(self):
        self._dialog = QFileDialog(self, self.tr('Select Location'), self._ui.projectLocation.text())
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self._locationSelected)
        self._dialog.open()

    def _updateProjectPath(self):
        folderName = f'{self._ui.projectName.text()}{self._suffix}' if self._ui.projectName.text() else ''
        path = Path(self._ui.projectLocation.text()) / folderName
        self._ui.folderName.setText(folderName)

        self._validatedPath = None

        if not self._ui.projectName.text():
            self._ui.validationMessage.clear()
        elif path.exists():
            self._ui.validationMessage.setText(self.tr(f'{self._ui.projectLocation.text()} already exists.'))
        else:
            self._ui.validationMessage.clear()
            self._validatedPath = path

        self.pathChanged.emit(self._validatedPath)

    def _locationSelected(self, dir):
        self._ui.projectLocation.setText(str(Path(dir).resolve()))
        self._updateProjectPath()
