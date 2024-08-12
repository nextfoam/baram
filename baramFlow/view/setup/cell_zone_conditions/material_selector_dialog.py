#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum, auto

import qasync
from PySide6.QtWidgets import QDialog, QListWidgetItem
from PySide6.QtCore import Qt

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import Phase
from .materials_selector_dialog_ui import Ui_MaterialsSelectorDialog


class ItemDataRole(Enum):
    USER_DATA = Qt.UserRole
    FILTERING_TEXT = auto()
    SELECTION_FLAG = auto()
    LIST_INDEX = auto()


@dataclass
class SelectorItem:
    label: str
    text: str
    data: str


class MaterialSectorDialog(QDialog):
    def __init__(self, parent, primary: str, secondaries: list[str], cavitationConfigured):
        super().__init__(parent)
        self._ui = Ui_MaterialsSelectorDialog()
        self._ui.setupUi(self)

        self._cavitationConfigured = cavitationConfigured
        self._primary = None
        self._secondaries = None

        for mid, name, type_, phase in MaterialDB.getMaterials():
            index = self._ui.primary.count()
            self._ui.primary.addItem(name, mid)

            item = None
            if phase != Phase.SOLID.value:
                item = QListWidgetItem(name)
                item.setData(ItemDataRole.USER_DATA.value, mid)
                item.setData(ItemDataRole.FILTERING_TEXT.value, name.lower())
                item.setData(ItemDataRole.SELECTION_FLAG.value, False)

                self._ui.list.addItem(item)
                self._ui.primary.setItemData(index, self._ui.list.row(item), ItemDataRole.LIST_INDEX.value)

                if secondaries and mid in secondaries:
                    self._addSelectedItem(item)

                self._ui.secondariesSelector.setEnabled(True)

            if mid == primary:
                self._ui.primary.setCurrentText(name)
                if item:
                    self._hideItemFromList(item)

        self._connectSignalsSlots()

    def getPrimaryMaterial(self):
        return self._primary

    def getSecondaries(self):
        return self._secondaries

    def _connectSignalsSlots(self):
        self._ui.primary.currentIndexChanged.connect(self._primaryChanged)
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.list.itemDoubleClicked.connect(self._addClicked)
        self._ui.add.clicked.connect(self._addClicked)
        self._ui.remove.clicked.connect(self._removeClicked)
        self._ui.secondaries.itemDoubleClicked.connect(self._removeClicked)
        self._ui.ok.clicked.connect(self._accept)

    def _primaryChanged(self):
        for i in range(self._ui.list.count()):
            item = self._ui.list.item(i)
            self._showItemInList(item)
        self._ui.secondaries.clear()
        self._ui.list.clearSelection()

        primaryIndex = self._ui.primary.currentData(ItemDataRole.LIST_INDEX.value)
        if primaryIndex is None:
            self._ui.secondariesSelector.setEnabled(False)
        else:
            item = self._ui.list.item(primaryIndex)
            self._hideItemFromList(item)
            self._ui.secondariesSelector.setEnabled(True)

    def _filterChanged(self):
        text = self._ui.filter.text().lower()
        for i in range(self._ui.list.count()):
            item = self._ui.list.item(i)
            item.setHidden(text not in item.data(ItemDataRole.FILTERING_TEXT.value)
                           or item.data(ItemDataRole.SELECTION_FLAG.value))

    def _addClicked(self):
        for item in self._ui.list.selectedItems():
            self._addSelectedItem(item)

    def _removeClicked(self):
        for item in self._ui.secondaries.selectedItems():
            self._showItemInList(self._ui.list.item(item.data(ItemDataRole.LIST_INDEX.value)))
            self._ui.secondaries.takeItem(self._ui.secondaries.row(item))

    @qasync.asyncSlot()
    async def _accept(self):
        count = self._ui.secondaries.count()
        if count < 1:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Seconary Materials'))
            return

        primary = self._ui.primary.currentData(ItemDataRole.USER_DATA.value)
        secondaries = [
            str(self._ui.list.item(
                self._ui.secondaries.item(i).data(ItemDataRole.LIST_INDEX.value)).data(ItemDataRole.USER_DATA.value))
            for i in range(self._ui.secondaries.count())]

        if self._cavitationConfigured:
            if (count > 1
                    and not await AsyncMessageBox().confirm(
                        self, self.tr('Change Materials'),
                        self.tr('Mass Transfer can be simulated only for two phases.'
                                'Mass transfer setting is going to become inactive. Proceed?'))):
                return

            if MaterialDB.getPhase(primary) != Phase.GAS or MaterialDB.getPhase(secondaries[0]) != Phase.LIQUID:
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'),
                    self.tr('Primary material and Secondary Material should be gas and liquid phases respectively.'))
                return

        self._primary = primary
        self._secondaries = secondaries

        self.accept()

    def _addSelectedItem(self, item):
        self._hideItemFromList(item)
        item.setSelected(False)

        itemToAdd = QListWidgetItem(item.text())
        itemToAdd.setData(ItemDataRole.LIST_INDEX.value, self._ui.list.row(item))
        self._ui.secondaries.addItem(itemToAdd)

    def _hideItemFromList(self, item):
        item.setData(ItemDataRole.SELECTION_FLAG.value, True)
        item.setHidden(True)

    def _showItemInList(self, item):
        item.setData(ItemDataRole.SELECTION_FLAG.value, False)
        item.setHidden(self._ui.filter.text().lower() not in item.data(ItemDataRole.FILTERING_TEXT.value))
