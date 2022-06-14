#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem
from PySide6.QtCore import Qt

from .selector_dialog_ui import Ui_SelectorDialog


class ItemDataIndex(Enum):
    DISPLAY_TEXT = 0
    FILTERING_TEXT = auto()
    ID_DATA = auto()


class SelectorDialog(QDialog):
    def __init__(self, parent, title, label, items):
        """Constructs a new SelectorDialog

        Args:
            parent: Parent widget of the dialog
            title: Window title of the dialog
            label: The label of the item (object name)
            items: List of item tuples - [(text to display, text for filtering, data to identify the item), ...]
        """
        super().__init__(parent)
        self._ui = Ui_SelectorDialog()
        self._ui.setupUi(self)

        self.setWindowTitle(title)
        self._ui.label.setText(label)
        for data in items:
            item = QListWidgetItem(data[ItemDataIndex.DISPLAY_TEXT.value])
            item.setData(Qt.UserRole, data)
            self._ui.list.addItem(item)

        self._connectSignalsSlots()

    def selectedItem(self):
        return self._ui.list.currentItem().data(Qt.UserRole)[ItemDataIndex.ID_DATA.value]

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        self._ui.filter.clear()
        self._ui.list.clearSelection()
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.list.currentItemChanged.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self.accept)

    def _itemSelected(self):
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)

    def _filterChanged(self):
        filterText = self._ui.filter.text().lower()
        for i in range(self._ui.list.count()):
            item = self._ui.list.item(i)
            item.setHidden(filterText not in item.data(Qt.UserRole)[ItemDataIndex.FILTERING_TEXT.value])
