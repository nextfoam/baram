#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal

from coredb import coredb
from coredb.material_db import ListIndex
from coredb.cell_zone_db import CellZoneListIndex, RegionDB
from .region_widget_ui import Ui_RegionWidget


class RegionWidget(QWidget):
    regionSelected = Signal(str)
    regionDoubleClicked = Signal(str)

    def __init__(self, name):
        super().__init__()
        self._ui = Ui_RegionWidget()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._name = name
        self._dialog = None

        self._connectSignalsSlots()
        self._load()

    @property
    def name(self):
        return self._name

    def material(self):
        return self._ui.material.currentData()

    def currentCellZone(self):
        return self._ui.list.currentItem().data(Qt.UserRole)

    def setMaterials(self, materials):
        material = self._db.getValue(RegionDB.getXPath(self._name) + '/material')

        self._ui.material.clear()
        for m in materials:
            self._ui.material.addItem(m[ListIndex.NAME.value], m[ListIndex.ID.value])
            if m[ListIndex.ID.value] == int(material):
                self._ui.material.setCurrentText(m[ListIndex.NAME.value])

    def clearSelection(self):
        self._ui.list.clearSelection()

    def _load(self):
        self._ui.groupBox.setTitle(self._name)

        cellZones = self._db.getCellZones(self._name)
        for c in cellZones:
            item = QListWidgetItem(c[CellZoneListIndex.NAME.value], self._ui.list)
            item.setData(Qt.UserRole, c[CellZoneListIndex.ID.value])

    def _connectSignalsSlots(self):
        self._ui.list.currentItemChanged.connect(self._cellZoneSelected)
        self._ui.list.itemDoubleClicked.connect(self._cellZoneDoubleClicked)

    def _cellZoneSelected(self):
        self.regionSelected.emit(self._name)

    def _cellZoneDoubleClicked(self):
        self.regionDoubleClicked.emit(self._name)
