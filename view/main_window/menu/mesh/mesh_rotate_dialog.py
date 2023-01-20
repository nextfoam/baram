#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog

from .mesh_rotate_dialog_ui import Ui_MeshRotateDialog


class MeshRotateDialog(QDialog):
    def __init__(self, parent, manager):
        super().__init__(parent)
        self._ui = Ui_MeshRotateDialog()
        self._ui.setupUi(self)

        self._manager = manager

    @qasync.asyncSlot()
    async def accept(self):
        self.close()

        origin = (self._ui.originX.text(), self._ui.originY.text(), self._ui.originZ.text())
        axis = (self._ui.axisX.text(), self._ui.axisY.text(), self._ui.axisZ.text())
        self._manager.rotate(origin, axis, self._ui.rotationAngle.text())

        super().accept()
