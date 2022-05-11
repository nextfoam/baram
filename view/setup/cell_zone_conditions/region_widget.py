#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QListWidgetItem
from PySide6.QtCore import Qt

from .region_widget_ui import Ui_RegionWidget


class RegionWidget(QWidget):
    def __init__(self, parent, region):
        super().__init__()
        self._ui = Ui_RegionWidget()
        self._ui.setupUi(self)

        self._parent = parent
        self._regionId = region["id"]

        self._setup(region)

        self._connectSignalsSlots()

    @property
    def regionId(self):
        return self._regionId

    def clearSelection(self):
        self._ui.list.clearSelection()

    def _setup(self, region):
        self._ui.groupBox.setTitle(region["name"])

        for cellZone in region["cellZones"]:
            item = QListWidgetItem(cellZone, self._ui.list)
            item.setData(Qt.UserRole, cellZone)

        item = QListWidgetItem("All", self._ui.list)
        item.setData(Qt.UserRole, "All")

    def _connectSignalsSlots(self):
        self._ui.list.currentItemChanged.connect(self._cellZoneSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)

    def _cellZoneSelected(self):
        self._parent.regionSelected(self._regionId)

    def _edit(self):
        self._parent.edit()
