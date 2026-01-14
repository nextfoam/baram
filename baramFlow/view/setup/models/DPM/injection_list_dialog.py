#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QListWidgetItem

from baramFlow.base.model.DPM_model import Injection
from widgets.async_message_box import AsyncMessageBox
from .injection_list_dialog_ui import Ui_InjectionListDialog
from .injection_dialog import InjectionDialog
from .injection_widget import InjectionWidget


class InjectionItem(QListWidgetItem):
    def __init__(self, parent, injection):
        super().__init__(parent)

        self._injection = injection
        self._widget = InjectionWidget(injection)

        self.setSizeHint(self._widget.sizeHint())
        parent.setItemWidget(self, self._widget)

    def injection(self):
        return self._widget.injection()

    def setInjection(self, injection):
        self._widget.setInjection(injection)


class InjectionListDialog(QDialog):
    def __init__(self, parent, injections):
        super().__init__(parent)
        self._ui = Ui_InjectionListDialog()
        self._ui.setupUi(self)

        self._dialog = None

        for i in injections:
            self._add(i)

        self._connectSignalsSlots()

        self._updateEditEnabled()

    def injections(self):
        return [self._ui.list.item(i).injection() for i in range(self._ui.list.count())]

    def _connectSignalsSlots(self):
        self._ui.list.itemSelectionChanged.connect(self._updateEditEnabled)
        self._ui.list.itemDoubleClicked.connect(self._openEditDialog)
        self._ui.add.clicked.connect(self._openAddDialog)
        self._ui.edit.clicked.connect(self._editClicked)
        self._ui.delete_.clicked.connect(self._delete)

    def _updateEditEnabled(self):
        if self._ui.list.selectedItems():
            self._ui.edit.setEnabled(True)
            self._ui.delete_.setEnabled(True)
        else:
            self._ui.edit.setEnabled(False)
            self._ui.delete_.setEnabled(False)

    def _openEditDialog(self, item):
        def update():
            item.setInjection(self._dialog.injection())
            self._ui.ok.setEnabled(True)

        self._dialog = InjectionDialog(self, item.injection(), self._usedNames())
        self._dialog.accepted.connect(update)
        self._dialog.open()

    def _openAddDialog(self):
        def add():
            self._add(self._dialog.injection())
            self._ui.ok.setEnabled(True)

        self._dialog = InjectionDialog(self, Injection.new(), self._usedNames())
        self._dialog.accepted.connect(add)
        self._dialog.open()

    def _editClicked(self):
        self._openEditDialog(self._ui.list.currentItem())

    @qasync.asyncSlot()
    async def _delete(self):
        if await AsyncMessageBox().confirm(self, self.tr('Delete Injection'),
                                     self.tr('Delete {}?'.format(self._ui.list.currentItem().injection().name))):
            self._ui.list.takeItem(self._ui.list.currentRow())
            self._updateEditEnabled()
            self._ui.ok.setEnabled(True)

    def _add(self, injection):
        InjectionItem(self._ui.list, injection)

    def _usedNames(self):
        return [self._ui.list.item(i).injection().name for i in range(self._ui.list.count())]
