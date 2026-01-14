#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Any

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt

from .selector_dialog_ui import Ui_SelectorDialog


class ListDataRole(IntEnum):
    USER_DATA = Qt.UserRole
    FILTERING_TEXT = auto()


@dataclass
class SelectorItem:
    label: str
    text: str
    data: Any


class SelectorDialog(QDialog):
    def __init__(self, parent, title, label, items, labelForNone=None, exclude=None):
        """Constructs a new SelectorDialog

        Args:
            parent: Parent widget of the dialog
            title: Window title of the dialog
            label: The label of the item (object name)
            items: List of items
            labelForNone: Text indicating that nothing is selected. None if item selection is required.
        """
        super().__init__(parent)
        self._ui = Ui_SelectorDialog()
        self._ui.setupUi(self)

        self.setWindowTitle(title)
        self._ui.label.setText(label)

        if labelForNone:
            item = QListWidgetItem(labelForNone)
            item.setData(ListDataRole.USER_DATA, None)
            item.setData(ListDataRole.FILTERING_TEXT, '')
            self._ui.list.addItem(item)

        for data in items:
            if exclude is None or data.data != exclude:
                item = QListWidgetItem(data.label)
                item.setData(ListDataRole.USER_DATA, data.data)
                item.setData(ListDataRole.FILTERING_TEXT, data.text.lower())
                self._ui.list.addItem(item)

        self._connectSignalsSlots()

    def setMultiSelectionMode(self):
        self._ui.list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

    def selectedItem(self):
        return self._ui.list.currentItem().data(ListDataRole.USER_DATA)

    def selectedItems(self):
        return [item.data(ListDataRole.USER_DATA) for item in self._ui.list.selectedItems()]

    def selectedText(self):
        return self._ui.list.currentItem().text()

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        self._ui.filter.clear()
        self._ui.list.clearSelection()
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.list.itemClicked.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self.accept)

    def _itemSelected(self):
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)

    def _filterChanged(self):
        filterText = self._ui.filter.text().lower()
        for i in range(self._ui.list.count()):
            item = self._ui.list.item(i)
            item.setHidden(filterText not in item.data(ListDataRole.FILTERING_TEXT))
