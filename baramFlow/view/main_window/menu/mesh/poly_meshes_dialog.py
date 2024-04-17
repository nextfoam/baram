#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto
from pathlib import Path

import qasync
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QTreeWidgetItem, QMessageBox, QDialogButtonBox, QHeaderView

from widgets.async_message_box import AsyncMessageBox
from widgets.flat_push_button import FlatPushButton

from .poly_mesh_selection_dialog import PolyMesheSelectionDialog
from .poly_meshes_dialog_ui import Ui_PolyMeshesDialog


removeIcon = QIcon(':/icons/trash-outline.svg')


class Column(IntEnum):
    NAME    = 0
    PATH    = auto()
    REMOVE  = auto()


class PolyMeshesDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_PolyMeshesDialog()
        self._ui.setupUi(self)

        self._dialog = None
        self._data = []

        self._ui.polyMeshes.setColumnWidth(Column.REMOVE, 20)
        self._ui.polyMeshes.header().setSectionResizeMode(Column.NAME, QHeaderView.ResizeMode.ResizeToContents)
        self._ui.polyMeshes.header().setSectionResizeMode(Column.PATH, QHeaderView.ResizeMode.ResizeToContents)
        self._ui.polyMeshes.header().setSectionResizeMode(Column.REMOVE, QHeaderView.ResizeMode.Fixed)

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._connectSignalsSlots()

    def data(self):
        return self._data

    def accept(self):
        self._data = []
        for i in range(self._ui.polyMeshes.topLevelItemCount()):
            item = self._ui.polyMeshes.topLevelItem(i)
            self._data.append((item.text(Column.NAME), Path(item.text(Column.PATH))))

        super().accept()

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._openSelectionDialog)

    def _openSelectionDialog(self):
        self._dialog = PolyMesheSelectionDialog(self)
        self._dialog.accepted.connect(self._addPolyMesh)
        self._dialog.open()

    def _addPolyMesh(self):
        rname, path = self._dialog.data()
        item = QTreeWidgetItem(self._ui.polyMeshes, [rname, path])
        button = FlatPushButton(removeIcon, '')
        button.clicked.connect(lambda: self._removePolyMesh(item))
        self._ui.polyMeshes.setItemWidget(item, Column.REMOVE, button)
        self._updateAcceptablility()

    @qasync.asyncSlot()
    async def _removePolyMesh(self, item):
        confirm = await AsyncMessageBox().question(self, self.tr('Remove PolyMesh From Selections'),
                                                   self.tr('Remove region {}?').format(item.text(Column.NAME)))
        if confirm == QMessageBox.StandardButton.Yes:
            self._ui.polyMeshes.takeTopLevelItem(self._ui.polyMeshes.indexOfTopLevelItem(item))
            self._updateAcceptablility()

    def _updateAcceptablility(self):
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self._ui.polyMeshes.topLevelItemCount() > 1)
