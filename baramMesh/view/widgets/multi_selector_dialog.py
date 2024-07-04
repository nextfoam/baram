#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtWidgets import QDialog, QListWidgetItem
from PySide6.QtCore import Qt, Signal

from .multi_selector_dialog_ui import Ui_MultiSelectorDialog


class ListDataRole(Enum):
    USER_DATA = Qt.UserRole
    FILTERING_TEXT = auto()
    SELECTION_FLAG = auto()


@dataclass
class SelectorItem:
    label: str  # Text to display in the list
    text: str   # Text for filtering
    value: str  # The key of item


class MultiSelectorDialog(QDialog):
    itemsSelected = Signal(list)

    def __init__(self, parent, title, items: list[SelectorItem], selectedItems):
        """Constructs a new SelectorDialog

        Args:
            title: Window title of the dialog
            items: List of items
            selectedItems: List of values for the selected item
        """
        super().__init__(parent)
        self._ui = Ui_MultiSelectorDialog()
        self._ui.setupUi(self)

        self.setWindowTitle(title)
        for data in items:
            item = QListWidgetItem(data.label)
            item.setData(ListDataRole.USER_DATA.value, data.value)
            item.setData(ListDataRole.FILTERING_TEXT.value, data.text.lower())
            item.setData(ListDataRole.SELECTION_FLAG.value, False)

            self._ui.list.addItem(item)
            if data.value in selectedItems:
                self._addSelectedItem(item)

        self._connectSignalsSlots()

    def selectedItems(self):
        return [(self._ui.list.item(self._ui.selectedList.item(i).data(Qt.UserRole)).data(ListDataRole.USER_DATA.value),
                 self._ui.selectedList.item(i).text())
                for i in range(self._ui.selectedList.count())]

    def accept(self):
        self.itemsSelected.emit(self.selectedItems())
        super().accept()

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
            item.setHidden(text not in item.data(ListDataRole.FILTERING_TEXT.value)
                           or item.data(ListDataRole.SELECTION_FLAG.value))

    def _addClicked(self):
        for item in self._ui.list.selectedItems():
            self._addSelectedItem(item)

    def _removeClicked(self):
        for item in self._ui.selectedList.selectedItems():
            i = self._ui.list.item(item.data(Qt.UserRole))
            i.setData(ListDataRole.SELECTION_FLAG.value, False)
            i.setHidden(False)
            self._ui.selectedList.takeItem(self._ui.selectedList.row(item))

    def _addSelectedItem(self, item):
        item.setData(ListDataRole.SELECTION_FLAG.value, True)
        item.setHidden(True)
        item.setSelected(False)

        itemToAdd = QListWidgetItem(item.text())
        itemToAdd.setData(Qt.UserRole, self._ui.list.row(item))
        self._ui.selectedList.addItem(itemToAdd)
