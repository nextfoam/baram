#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from .monitors_widget import MonitorsWidget
from .volume_dialog import VolumeDialog


class VolumesWidget(MonitorsWidget):
    def __init__(self):
        super().__init__(self.tr("Volumes"))

        self._db = coredb.CoreDB()
        self._dialog = None

        self._setListItems(self._db.getVolumeMonitors())

    def _addClicked(self):
        self._dialog = VolumeDialog(self)
        self._dialog.accepted.connect(self._addDialogAccepted)
        self._dialog.open()

    def _editClicked(self):
        self._dialog = VolumeDialog(self, self._ui.list.currentItem().text())
        self._dialog.open()

    def _deleteClicked(self):
        row = self._currentRow()
        name = self._itemText(row)
        confirm = QMessageBox.question(self, self.tr("Remove monitor item"),
                                       self.tr(f'Remove "{name}"?'))
        if confirm == QMessageBox.Yes:
            self._db.removeVolumeMonitor(name)
            self._removeItem(row)

    def _addDialogAccepted(self):
        self._addItem(self._dialog.getName())
