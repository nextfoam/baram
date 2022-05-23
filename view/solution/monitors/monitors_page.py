#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtWidgets import QWidget, QDialog, QMessageBox
from PySide6.QtCore import Qt

from .monitors_page_ui import Ui_MonitorsPage
from .force_dialog import ForceDialog
from .point_dialog import PointDialog
from .surface_dialog import SurfaceDialog
from .volume_dialog import VolumeDialog


class MonitorsPage(QWidget):
    class MonitorTarget:
        class BUTTON(Enum):
            ADD = -2
            EDIT = -3
            DELETE = -4

        def __init__(self, parent, name, listView, buttonGroup, prefix, addSlot, editSlot, deleteSlot):
            self._parent = parent
            self._prefix = prefix
            self._list = listView
            self._buttonGroup = buttonGroup
            self._addSlot = addSlot
            self._editSlot = editSlot
            self._deleteSlot = deleteSlot

            self._connectSignalsSlots()

        def _connectSignalsSlots(self):
            self._list.currentItemChanged.connect(self._itemSelected)
            self._buttonGroup.button(self.BUTTON.ADD.value).clicked.connect(self._add)
            self._buttonGroup.button(self.BUTTON.EDIT.value).clicked.connect(self._edit)
            self._buttonGroup.button(self.BUTTON.DELETE.value).clicked.connect(self._delete)

        def _itemSelected(self, item):
            self._buttonGroup.button(self.BUTTON.EDIT.value).setEnabled(True)
            self._buttonGroup.button(self.BUTTON.DELETE.value).setEnabled(True)

        def _add(self):
            name = self._addSlot(self._newName())
            if name:
                self._list.addItem(name)
                self._list.scrollToBottom()

        def _edit(self):
            self._editSlot(self._list.currentItem().text())

        def _delete(self):
            confirm = QMessageBox.question(
                self._parent, self._parent.tr("Remove monitor item"),
                self._parent.tr('Remove "{item}"').format(item=self._list.currentItem().text()))
            if confirm == QMessageBox.Yes:
                self._deleteSlot()
                self._list.takeItem(self._list.currentRow())

        def _newName(self):
            i = 0
            while True:
                name = f"{self._prefix}-{i}"
                if not self._list.findItems(name, Qt.MatchFlag.MatchExactly):
                    return name
                i = i + 1

    def __init__(self):
        super().__init__()
        self._ui = Ui_MonitorsPage()
        self._ui.setupUi(self)

        self.forces = self.MonitorTarget(self, "force", self._ui.forces, self._ui.forceButtons, "Force",
                                           self._addForce, self._editForce, self._deleteForce)
        self.points = self.MonitorTarget(self, "point", self._ui.points, self._ui.pointButtons, "point-mon",
                                           self._addPoint, self._editPoint, self._deletePoint)
        self.Surfaces = self.MonitorTarget(self, "surface", self._ui.surfaces, self._ui.surfaceButtons, "surface-mon",
                                             self._addSurface, self._editSurface, self._deleteSurface)
        self.Volumes = self.MonitorTarget(self, "volume", self._ui.volumes, self._ui.volumeButtons, "volume-mon",
                                            self._addVolume, self._editVolume, self._deleteVolume)

    def load(self):
        pass

    def save(self):
        pass

    def _addForce(self, name):
        dialog = ForceDialog(name)
        if dialog.exec() == QDialog.Accepted:
            return dialog.getName()
        return None

    def _editForce(self, name):
        dialog = ForceDialog(name, False)
        if dialog.exec() == QDialog.Accepted:
            pass

    def _deleteForce(self):
        return

    def _addPoint(self, name):
        dialog = PointDialog(name)
        if dialog.exec() == QDialog.Accepted:
            return dialog.getName()
        return None

    def _editPoint(self, name):
        dialog = PointDialog(name, False)
        if dialog.exec() == QDialog.Accepted:
            pass

    def _deletePoint(self):
        pass

    def _addSurface(self, name):
        dialog = SurfaceDialog(name)
        if dialog.exec() == QDialog.Accepted:
            return dialog.getName()
        return None

    def _editSurface(self, name):
        dialog = SurfaceDialog(name, False)
        if dialog.exec() == QDialog.Accepted:
            pass

    def _deleteSurface(self):
        pass

    def _addVolume(self, name):
        dialog = VolumeDialog(name)
        if dialog.exec() == QDialog.Accepted:
            return dialog.getName()
        return None

    def _editVolume(self, name):
        dialog = VolumeDialog(name, False)
        if dialog.exec() == QDialog.Accepted:
            pass

    def _deleteVolume(self):
        pass
