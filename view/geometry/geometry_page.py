#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QTreeWidgetItem
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QIcon

from app import app
from view.widgets.icon_check_box import IconCheckBox
from .geometry_add_dialog import GeometryAddDialog
from .geometry_dialog import GeometryDialog
from .geometry_page_ui import Ui_GeometryPage


class GeometryItem(QObject):
    checkStateChanged = Signal(int)

    icon = QIcon(':/icons/prism.svg')

    def __init__(self, tree, gId, geometry):
        super().__init__()
        self._tree = tree
        self._item = QTreeWidgetItem(tree, gId)
        self._checkBox = IconCheckBox(':/icons/eye.svg', ':/icons/eye-off.svg')

        tree.setItemWidget(self._item, 1, self._checkBox)
        self._item.setIcon(2, self.icon)
        self._item.setText(3, geometry['name'])

        self._checkBox.checkStateChanged.connect(self._checkStateChanged)

    def _checkStateChanged(self, state):
        self.checkStateChanged.emit(self._item.type())

    def isChecked(self):
        return self._checkBox.isChecked()


class GeometryList(QObject):
    geometryCheckStateChanged = Signal(int)

    def __init__(self, tree):
        super().__init__()
        self._tree = tree
        self._tree.expandAll()
        self._items = {}

        self._tree.setColumnWidth(0, 0)
        self._tree.setColumnWidth(1, 40)
        self._tree.setColumnWidth(2, 20)

    def add(self, gId, geometry):
        self._items[gId] = GeometryItem(self._tree, gId, geometry)
        self._items[gId].checkStateChanged.connect(self.geometryCheckStateChanged)

    def remove(self, gId):
        index = -1

        for i in range(self._tree.topLevelItemCount()):
            if self._tree.topLevelItem(i).type() == gId:
                index = i
                break

        if index > -1:
            item = self._tree.takeTopLevelItem(index)
            del self._items[gId]
            del item

    def isGeometryChecked(self, gId):
        return self._items[gId].isChecked()

    def currentGId(self):
        return self._tree.currentItem().type()


class GeometryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_GeometryPage()
        self._ui.setupUi(self)

        self._list = GeometryList(self._ui.list)
        self._addDialog = None
        self._dialog = GeometryDialog(self)

        self._connectSignalsSlots()
        self._load()

    def title(self):
        return self.tr('Geometry')

    def _connectSignalsSlots(self):
        self._list.geometryCheckStateChanged.connect(self._setGeometryVisibliity)

        self._ui.import_.clicked.connect(self._importClicked)
        self._ui.add.clicked.connect(self._addClicked)
        self._ui.edit.clicked.connect(self._editClicked)
        self._ui.remove.clicked.connect(self._removeGeometry)

        self._dialog.geometryAdded.connect(self._addToList)
        self._dialog.geometryEdited.connect(self._updateGeometry)

    def _importClicked(self):
        return

    def _addClicked(self):
        self._addDialog = GeometryAddDialog(self)
        self._addDialog.accepted.connect(self._openDialogToAdd)
        self._addDialog.open()

    def _editClicked(self):
        return

    def _removeGeometry(self):
        gId = self._list.currentGId()

        db = app.db.checkout()
        db.removeElement('geometry', gId)
        app.db.commit(db)

        self._list.remove(gId)

    def _load(self):
        geometry = app.db.getElements('geometry', ['name', 'gType'])
        for gid in geometry:
            self._list.add(gid, geometry[gid])

    def _setGeometryVisibliity(self, gId):
        print('eye toggled', gId, self._list.isGeometryChecked(gId))

    def _openDialogToAdd(self):
        self._dialog.setupForAdding(*self._addDialog.geometryInfo())
        self._dialog.open()

    def _addToList(self, gId):
        self._list.add(gId, app.db.getElement('geometry', gId))

    def _updateGeometry(self):
        return
