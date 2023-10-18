#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt

from baramFlow.coredb import coredb
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.view.widgets.content_page import ContentPage
from .cell_zone_conditions_page_ui import Ui_CellZoneConditionsPage
from .cell_zone_condition_dialog import CellZoneConditionDialog
from .cell_zone_widget import CellZoneWidget


class CellZoneConditionsPage(ContentPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_CellZoneConditionsPage()
        self._ui.setupUi(self)

        self._singleRegion = False

        self._connectSignalsSlots()

        self._load()

    def _load(self):
        regions = coredb.CoreDB().getRegions()
        if len(regions) == 1 and not regions[0]:
            self._singleRegion = True
            item = QTreeWidgetItem(self._ui.cellZones, [DEFAULT_REGION_NAME], 0)
            self._addCellZones(item, '')
        else:
            self._singleRegion = False
            for rname in regions:
                item = QTreeWidgetItem(self._ui.cellZones, [rname], 0)
                self._addCellZones(item, rname)

        self._ui.cellZones.expandAll()

    def _connectSignalsSlots(self):
        self._ui.cellZones.doubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)

    def _edit(self):
        item = self._ui.cellZones.currentItem()
        czid = item.type()
        if czid:
            self._dialog = CellZoneConditionDialog(self, czid)
            self._dialog.accepted.connect(self._ui.cellZones.itemWidget(item, 0).updateType)
        else:
            self._dialog = CellZoneConditionDialog(
                self, item.data(0, Qt.UserRole), '' if self._singleRegion else item.text(0))

        self._dialog.open()

    def _addCellZones(self, parent, rname):
        cellZones = coredb.CoreDB().getCellZones(rname)
        for czid, czname in cellZones:
            if CellZoneDB.isRegion(czname):
                parent.setData(0, Qt.UserRole, czid)
            else:
                item = QTreeWidgetItem(parent, czid)
                cellZoneWidget = CellZoneWidget(czid, czname)
                self._ui.cellZones.setItemWidget(item, 0, cellZoneWidget)
                item.setFirstColumnSpanned(True)

    def _region(self, index):
        item = self._ui.cellZones.topLevelItem(index)
        return '' if self._singleRegion else item.text(0),  self._ui.cellZones.itemWidget(item, 1)
