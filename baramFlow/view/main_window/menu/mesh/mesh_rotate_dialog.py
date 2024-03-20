#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .mesh_rotate_dialog_ui import Ui_MeshRotateDialog


class MeshRotateDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MeshRotateDialog()
        self._ui.setupUi(self)

    def data(self):
        return ((self._ui.originX.text(), self._ui.originY.text(), self._ui.originZ.text()),
                (self._ui.axisX.text(), self._ui.axisY.text(), self._ui.axisZ.text()),
                self._ui.rotationAngle.text())
