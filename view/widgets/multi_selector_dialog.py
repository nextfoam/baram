#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QDialog, QListWidgetItem
from PySide6.QtCore import Qt

from .multi_selector_dialog_ui import Ui_MultiSelectorDialog


class ItemDataIndex(Enum):
    DISPLAY_TEXT = 0
    FILTERING_TEXT = auto()
    ID_DATA = auto()


class ListDataType(Enum):
    USER_DATA = Qt.UserRole
    FILTERING_TEXT = auto()
    SELECTION_FLAG = auto()


class MultiSelectorDialog(QDialog):
    def __init__(self, parent, title, items, selectedItems):
        """Constructs a new SelectorDialog

        Args:
            title: Window title of the dialog
            items: List of item tuples - [(text to display, text for filtering, id), ...]
            selectedItems: List of ids of selected items
        """
        super().__init__()
        self._ui = Ui_MultiSelectorDialog()
        self._ui.setupUi(self)

        self.setWindowTitle(title)
        for data in items:
            item = QListWidgetItem(data[ItemDataIndex.DISPLAY_TEXT.value])
            item.setData(ListDataType.USER_DATA.value, data[ItemDataIndex.ID_DATA.value])
            item.setData(ListDataType.FILTERING_TEXT.value, data[ItemDataIndex.FILTERING_TEXT.value])
            item.setData(ListDataType.SELECTION_FLAG.value, False)

            self._ui.list.addItem(item)
            if data[ItemDataIndex.ID_DATA.value] in selectedItems:
                self._addItem(item)

        self._connectSignalsSlots()

    def selectedItems(self):
        return [self._ui.list.item(self._ui.selectedList.item(i).data(Qt.UserRole)).data(ListDataType.USER_DATA.value)
                for i in range(self._ui.selectedList.count())]

    def _connectSignalsSlots(self):
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.list.itemDoubleClicked.connect(self._addClicked)
        self._ui.add.clicked.connect(self._addClicked)
        self._ui.remove.clicked.connect(self._removeClicked)
        self._ui.selectedList.itemDoubleClicked.connect(self._removeClicked)

    def _filterChanged(self):
        text = self._ui.filter.text().lower()
        for i in range(self._ui.list.count()):
            item = self._ui.list.item(i)
            item.setHidden(text not in item.data(ListDataType.FILTERING_TEXT.value)
                           or item.data(ListDataType.SELECTION_FLAG.value))

    def _addClicked(self):
        for item in self._ui.list.selectedItems():
            self._addItem(item)

    def _removeClicked(self):
        for item in self._ui.selectedList.selectedItems():
            i = self._ui.list.item(item.data(Qt.UserRole))
            i.setData(ListDataType.SELECTION_FLAG.value, False)
            i.setHidden(False)
            self._ui.selectedList.takeItem(self._ui.selectedList.row(item))

    def _addItem(self, item):
        item.setData(ListDataType.SELECTION_FLAG.value, True)
        item.setHidden(True)
        item.setSelected(False)

        itemToAdd = QListWidgetItem(item.text())
        itemToAdd.setData(Qt.UserRole, self._ui.list.row(item))
        self._ui.selectedList.addItem(itemToAdd)
