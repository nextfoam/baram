#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QLineEdit

from .volume_dialog_ui import Ui_VolumeDialog


class VolumeDialog(QDialog):
    def __init__(self, name, new=True):
        """Constructs volume monitor setup dialog.

        Args:
            new: Whether to create new monitor item. If true, name is editable.
        """
        super().__init__()
        self._ui = Ui_VolumeDialog()
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
