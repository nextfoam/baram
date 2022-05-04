#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem
from PySide6.QtCore import Qt

from view.widgets.selector_dialog_ui import Ui_SelectorDialog


class SelectorDialog(QDialog):
    def __init__(self, label, items):
        super().__init__()
        self._ui = Ui_SelectorDialog()
        self._ui.setupUi(self)

        self._setup(label, items)
        self._connectSignalsSlots()

    def selectedItem(self):
        return self._ui.list.currentItem().data(Qt.UserRole)[0]

    def showEvent(self, event):
        self._ui.filter.clear()
        self._ui.list.clearSelection()
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        return super().showEvent(event)

    def _setup(self, label, items):
        self._ui.label.setText(label)
        if isinstance(items, dict):
            for key, value in items.items():
                item = QListWidgetItem(value)
                item.setData(Qt.UserRole, [key, key.lower()])
                self._ui.list.addItem(item)
        else:
            for value in items:
                item = QListWidgetItem(value)
                item.setData(Qt.UserRole, [value, value.lower()])
                self._ui.list.addItem(item)

    def _connectSignalsSlots(self):
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.list.currentItemChanged.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self.accept)

    def _itemSelected(self):
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)

    def _filterChanged(self):
        filter = self._ui.filter.text().lower()
        for i in range(self._ui.list.count()):
            item = self._ui.list.item(i)
            item.setHidden(filter not in item.data(Qt.UserRole)[1])
