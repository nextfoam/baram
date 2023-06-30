#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QDialogButtonBox

from .geometry_add_dialog_ui import Ui_GeometryAddDialog


class GeometryAddDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_GeometryAddDialog()
        self._ui.setupUi(self)

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(self.tr('Next'))
        self._validate()
        self._ui.name.textChanged.connect(self._validate)

    def geometryInfo(self):
        return self._ui.name.text(), self._ui.shapeRadios.checkedButton().objectName()

    def _validate(self):
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self._ui.name.text().strip() != '')
