#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QDialog, QListWidgetItem
from PySide6.QtCore import Qt

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from .region_objects_selector_ui import Ui_RegionObjectsSelector


class ListDataRole(Enum):
    USER_DATA = Qt.UserRole
    FILTERING_TEXT = auto()
    SELECTION_FLAG = auto()


class RegionObjectsSelector(QDialog):
    def __init__(self, parent, title, selectedItems):
        """Constructs a new SelectorDialog

        Args:
            title: Window title of the dialog
            selectedItems: List of ids of selected items
        """
        super().__init__(parent)
        self._ui = Ui_RegionObjectsSelector()
        self._ui.setupUi(self)

        self._regions = coredb.CoreDB().getRegions()

        self.setWindowTitle(title)

        if len(self._regions) == 1 and not self._regions[0]:
            self._ui.regionWidget.hide()
        self._ui.region.addItems(self._regions)

        if selectedItems:
            self._ui.region.setCurrentText(BoundaryDB.getBoundaryRegion(selectedItems[0]))
        self._regionChanged(self._ui.region.currentText())

        for b in selectedItems:
            bcid = int(b)
            for row in range(self._ui.list.count()):
                item = self._ui.list.item(row)
                if item.data(ListDataRole.USER_DATA.value) == bcid:
                    item.setData(ListDataRole.SELECTION_FLAG.value, True)
                    item.setHidden(True)

                    itemToAdd = QListWidgetItem(item.text())
                    itemToAdd.setData(Qt.UserRole, self._ui.list.row(item))
                    self._ui.selectedList.addItem(itemToAdd)

                    break

        self._connectSignalsSlots()

    def region(self):
        return self._ui.region.currentText()

    def selectedItems(self):
        return [self._ui.list.item(self._ui.selectedList.item(i).data(Qt.UserRole)).data(ListDataRole.USER_DATA.value)
                for i in range(self._ui.selectedList.count())]

    def _connectSignalsSlots(self):
        self._ui.region.currentTextChanged.connect(self._regionChanged)
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.list.itemDoubleClicked.connect(self._addClicked)
        self._ui.add.clicked.connect(self._addClicked)
        self._ui.remove.clicked.connect(self._removeClicked)
        self._ui.selectedList.itemDoubleClicked.connect(self._removeClicked)

    def _regionChanged(self, text):
        self._ui.filter.clear()
        self._ui.list.clear()
        self._ui.selectedList.clear()
        self._loadItems(text)

    def _addItem(self, id_, name):
        item = QListWidgetItem(name)
        item.setData(ListDataRole.USER_DATA.value, id_)
        item.setData(ListDataRole.FILTERING_TEXT.value, name.lower())
        item.setData(ListDataRole.SELECTION_FLAG.value, False)
        self._ui.list.addItem(item)

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

    def _loadItems(self, region):
        raise NotImplementedError


class BoundariesSelector(RegionObjectsSelector):
    def __init__(self, parent, selectedItems):
        super().__init__(parent, self.tr("Select Boundaries"), selectedItems)

    def _loadItems(self, region):
        boundaries = coredb.CoreDB().getBoundaryConditions(region)
        for bcid, bcname, bctype in boundaries:
            self._addItem(bcid, bcname)


class CellZonesSelector(RegionObjectsSelector):
    def __init__(self, parent, selectedItems):
        super().__init__(parent, self.tr("Select Cell Zones"), selectedItems)

    def _loadItems(self, region):
        cellZones = coredb.CoreDB().getCellZones(region)
        for czid, czname in cellZones:
            self._addItem(czid, czname)
