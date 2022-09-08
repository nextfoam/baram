#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .mesh_scale_dialog_ui import Ui_MeshScaleDialog


class MeshScaleDialog(QDialog):
    def __init__(self, parent, manager):
        super().__init__(parent)
        self._ui = Ui_MeshScaleDialog()
        self._ui.setupUi(self)

        self._manager = manager

    def accept(self):
        self.close()
        self._manager.scale(self._ui.factorX.text(), self._ui.factorY.text(), self._ui.factorZ.text())
        super().accept()

