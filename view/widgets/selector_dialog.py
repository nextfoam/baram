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

    def itemSelected(self):
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)

    def selectedItem(self):
        return self._ui.list.currentItem().data(Qt.UserRole)

    def showEvent(self, event):
        self._ui.list.clearSelection()
        self._ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        return super().showEvent(event)

    def _setup(self, label, items):
        self._ui.label.setText(label)
        if isinstance(items, dict):
            for key, value in items.items():
                item = QListWidgetItem(value)
                item.setData(Qt.UserRole, key)
                self._ui.list.addItem(item)
        else:
            self._ui.list.addItems(items)

    def _connectSignalsSlots(self):
        self._ui.list.currentItemChanged.connect(self.itemSelected)

