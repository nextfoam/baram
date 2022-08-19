#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from openfoam.run import runUtility
from openfoam.file_system import FileSystem
from .mesh_ratate_dialog_ui import Ui_MeshRatateDialog


class MeshRotateDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MeshRatateDialog()
        self._ui.setupUi(self)

    @qasync.asyncSlot()
    async def accept(self):
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self._ui.buttonBox.button(QDialogButtonBox.Cancel).setEnabled(False)

        origin = f'({self._ui.originX.text()} {self._ui.originY.text()} {self._ui.originZ.text()})'
        axis = f'({self._ui.axisX.text()} {self._ui.axisY.text()} {self._ui.axisZ.text()})'
        rotation = f'({axis} {self._ui.rotationAngle.text()})'
        result = await runUtility('transformPoints','-allRegions',  '-origin', origin, '-rotate-angle', rotation,
                                  cwd=FileSystem.caseRoot())

        if result != 0:
            QMessageBox.critical(self, self.tr('Mesh Rotation'), self.tr('Fail to mesh rotation.'))

        super().accept()
