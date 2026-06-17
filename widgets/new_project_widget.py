#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from pathlib import Path

from PySide6.QtCore import QRegularExpression, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QFileDialog, QWidget

from libbaram.openfoam.openfoam_path import getOpenFOAMPathError, OPENFOAM_PATH_PART_PATTERN

from .new_project_widget_ui import Ui_NewProjectWidget


class NewProjectWidget(QWidget):
    pathChanged = Signal(Path)

    def __init__(self, parent, path: Path = None, suffix=None):
        super().__init__(parent)

        self._ui = Ui_NewProjectWidget()
        self._ui.setupUi(self)
        self._ui.validationMessage.setVisible(True)

        self._suffix: str = ''

        self._validatedPath: Path | None = None
        self._locationError: str | None = None

        self._dialog = None

        self._ui.projectName.setValidator(QRegularExpressionValidator(QRegularExpression(OPENFOAM_PATH_PART_PATTERN)))

        self._setLocation(path if path and path.exists() else Path.home())

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
        self._dialog.fileSelected.connect(self._setLocation)
        self._dialog.open()

    def _updateProjectPath(self):
        folderName = f'{self._ui.projectName.text()}{self._suffix}' if self._ui.projectName.text() else ''
        path = Path(self._ui.projectLocation.text()) / folderName
        self._ui.folderName.setText(folderName)

        self._validatedPath = None
        if self._locationError is not None:
            return

        if folderName:
            if path.exists():
                self._ui.validationMessage.setText(self.tr('{0} already exists.'.format(path)))
            else:
                self._ui.validationMessage.clear()
                if folderName:
                    self._validatedPath = path
        else:
            self._ui.validationMessage.clear()

        self.pathChanged.emit(self._validatedPath)

    def _setLocation(self, location):
        path = Path(location).resolve()
        self._ui.projectLocation.setText(str(path))

        self._locationError = getOpenFOAMPathError(path)
        if self._locationError is None:
            self._updateProjectPath()
        else:
            self._ui.validationMessage.setText(self._locationError)
