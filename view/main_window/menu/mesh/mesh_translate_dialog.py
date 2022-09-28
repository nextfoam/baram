#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog

from .mesh_translate_dialog_ui import Ui_MeshTranslateDialog


class MeshTranslateDialog(QDialog):
    def __init__(self, parent, manager):
        super().__init__(parent)
        self._ui = Ui_MeshTranslateDialog()
        self._ui.setupUi(self)

        self._manager = manager

    @qasync.asyncSlot()
    async def accept(self):
        self.close()
        self._manager.translate(self._ui.offsetX.text(), self._ui.offsetY.text(), self._ui.offsetZ.text())
        super().accept()
