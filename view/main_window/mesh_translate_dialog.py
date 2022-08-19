#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from openfoam.run import runUtility
from openfoam.file_system import FileSystem
from .mesh_translate_dialog_ui import Ui_MeshTranslateDialog


class MeshTranslateDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MeshTranslateDialog()
        self._ui.setupUi(self)

    @qasync.asyncSlot()
    async def accept(self):
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self._ui.buttonBox.button(QDialogButtonBox.Cancel).setEnabled(False)

        offset = f'({self._ui.offsetX.text()} {self._ui.offsetY.text()} {self._ui.offsetZ.text()})'
        result = await runUtility('transformPoints', '-allRegions', '-translate', offset, cwd=FileSystem.caseRoot())

        if result != 0:
            QMessageBox.critical(self, self.tr('Mesh Translation'), self.tr('Fail to mesh translation.'))

        super().accept()
