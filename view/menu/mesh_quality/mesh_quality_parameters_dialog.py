#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .mesh_quality_parameters_dialog_ui import Ui_MeshQualityParametersDialog


class MeshQualityParametersDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MeshQualityParametersDialog()
        self._ui.setupUi(self)
