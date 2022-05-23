#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QLineEdit

from .surface_dialog_ui import Ui_SurfaceDialog


class SurfaceDialog(QDialog):
    def __init__(self, name, new=True):
        """Constructs surface monitor setup dialog.

        Args:
            new: Whether to create new surface item. If true, name is editable.
        """
        super().__init__()
        self._ui = Ui_SurfaceDialog()
        self._ui.setupUi(self)

        self._nameEdit = None

        self._setup(name, new)

    def setName(self, name):
        self._nameEdit.setText(name)

    def getName(self):
        return self._nameEdit.text()

    def _setup(self, name, new):
        if new:
            layout = self._ui.properties.layout()
            self._nameEdit = QLineEdit(name)
            layout.insertRow(0, "Name", self._nameEdit)
        else:
            self._ui.groupBox.setTitle(name)
