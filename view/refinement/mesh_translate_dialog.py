#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .mesh_translate_dialog_ui import Ui_MeshTranslateDialog


class MeshTranslateDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MeshTranslateDialog()
        self._ui.setupUi(self)

    def data(self):
        return self._ui.offsetX.text(), self._ui.offsetY.text(), self._ui.offsetZ.text()
