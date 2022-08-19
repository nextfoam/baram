#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from openfoam.run import runUtility
from openfoam.file_system import FileSystem
from .mesh_scale_dialog_ui import Ui_MeshScaleDialog


class MeshScaleDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MeshScaleDialog()
        self._ui.setupUi(self)

    @qasync.asyncSlot()
    async def accept(self):
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self._ui.buttonBox.button(QDialogButtonBox.Cancel).setEnabled(False)

        factor = f'({self._ui.factorX.text()} {self._ui.factorY.text()} {self._ui.factorZ.text()})'
        result = await runUtility('transformPoints','-allRegions',  '-scale', factor, cwd=FileSystem.caseRoot())

        if result != 0:
            QMessageBox.critical(self, self.tr('Mesh Scaling'), self.tr('Fail to mesh scaling.'))

        super().accept()

