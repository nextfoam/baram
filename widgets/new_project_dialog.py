#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox

from .new_project_dialog_ui import Ui_NewProjectDialog


class NewProjectDialog(QDialog):
    def __init__(self, parent, title, path=None):
        super().__init__(parent)

        self._ui = Ui_NewProjectDialog()
        self._ui.setupUi(self)

        self._complete = False
        self._baseLocation = Path.home() if path is None else path
        self._updateProjectLocation()

        self._dialog = None

        self.setWindowTitle(title)

        self._connectSignalsSlots()

    def projectLocation(self):
        return Path(self._ui.projectLocation.text())

    def _connectSignalsSlots(self):
        self._ui.projectName.textChanged.connect(self._updateProjectLocation)
        self._ui.select.clicked.connect(self._selectLocation)

    def _selectLocation(self):
        self._dialog = QFileDialog(self, self.tr('Select Location'), str(self._baseLocation))
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self._locationParentSelected)
        self._dialog.open()

    def _updateProjectLocation(self):
        self._ui.projectLocation.setText(str(self._baseLocation / self._ui.projectName.text()))

        complete = False

        if not self._baseLocation.exists():
            self._ui.validationMessage.setText(self.tr(f'{self._baseLocation} is not a directory.'))
        elif not self._ui.projectName.text():
            self._ui.validationMessage.clear()
        elif Path(self._ui.projectLocation.text()).exists():
            self._ui.validationMessage.setText(self.tr(f'{self._ui.projectLocation.text()} already exists.'))
        else:
            self._ui.validationMessage.clear()
            complete = True

        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(complete)

    def _locationParentSelected(self, dir):
        self._baseLocation = Path(dir).resolve()
        self._updateProjectLocation()
