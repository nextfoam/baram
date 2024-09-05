#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import qasync
from PySide6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox

from libbaram.openfoam.polymesh import isPolyMesh
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb.app_settings import AppSettings
from .poly_mesh_selection_dialog_ui import Ui_PolyMeshSelectionDialog


class PolyMesheSelectionDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_PolyMeshSelectionDialog()
        self._ui.setupUi(self)

        self._dialog = None

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._connectSignalsSlots()

    def data(self):
        return self._ui.regionName.text(), self._ui.polyMesh.text()

    def _connectSignalsSlots(self):
        self._ui.regionName.textChanged.connect(self._updateAcceptablility)
        self._ui.select.clicked.connect(self._openFileDialog)

    def _openFileDialog(self):
        self._dialog = QFileDialog(self, self.tr('Select Mesh Directory'), AppSettings.getRecentMeshDirectory())
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self._polyMeshSelected)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _polyMeshSelected(self, directory):
        if isPolyMesh(Path(directory)):
            self._ui.polyMesh.setText(directory)
            self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                len(self._ui.regionName.text().strip()))
            AppSettings.updateRecentMeshDirectory(str(directory))
        else:
            self._ui.polyMesh.clear()
            self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            await AsyncMessageBox().information(self, self.tr('PolyMesh Folder Selection'),
                                                self.tr(directory + ' is not a polyMesh directory.'))

    def _updateAcceptablility(self):
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            len(self._ui.regionName.text().strip()) and len(self._ui.polyMesh.text()))
