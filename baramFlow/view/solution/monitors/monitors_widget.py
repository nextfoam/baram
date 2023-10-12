#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .monitors_widget_ui import Ui_MonitorsWidget


class MonitorsWidget(QWidget):
    def __init__(self, label):
        super().__init__()
        self._ui = Ui_MonitorsWidget()
        self._ui.setupUi(self)

        self._ui.label.setText(label)

        self._connectSignalsSlots()

    def clear(self):
        self._ui.list.clear()

    def _setListItems(self, items):
        for i in items:
            self._ui.list.addItem(i)

    def _currentRow(self):
        return self._ui.list.currentRow()

    def _itemText(self, row):
        return self._ui.list.item(row).text()

    def _addItem(self, name):
        self._ui.list.addItem(name)

    def _removeItem(self, row):
        self._ui.list.takeItem(row)

    def _connectSignalsSlots(self):
        self._ui.list.currentItemChanged.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self._editClicked)
        self._ui.add.clicked.connect(self._addClicked)
        self._ui.edit.clicked.connect(self._editClicked)
        self._ui.delete_.clicked.connect(self._deleteClicked)

    def _itemSelected(self, item):
        self._ui.edit.setEnabled(True)
        self._ui.delete_.setEnabled(True)

    def _editClicked(self):
        raise NotImplementedError

    def _addClicked(self):
        raise NotImplementedError

    def _deleteClicked(self):
        raise NotImplementedError
