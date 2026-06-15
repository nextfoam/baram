#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from enum import Enum, auto

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QListWidgetItem, QWidget, QListWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.services.cell_zone.cell_zone_service import CellZoneService
from baramFlow.base.region.region_data import CellZoneModel
from baramFlow.coredb.cell_zone_db import copyCellZoneConditions

from .copy_dialog_ui import Ui_CopyDialog


class CopyMode(Enum):
    REGION = auto()
    CELL_ZONE = auto()


class CellZoneListItem(QListWidgetItem):
    def __init__(self, parent: QListWidget, cellZone: CellZoneModel):
        super().__init__(parent)

        self._czid: str = cellZone.czid
        self._textForFiltering: str = ''

        if cellZone.isRegion():
            self._textForFiltering = cellZone.rname.lower()
            self.setText(cellZone.rname)
        else:
            self._textForFiltering = cellZone.name.lower()
            self.setText(cellZone.scopedName)

    def czid(self):
        return self._czid

    def applyFilter(self, filterText):
        self.setHidden(filterText not in self._textForFiltering and not self.isSelected())


class Filter:
    def __init__(self, filter, list):
        self._filter = filter
        self._list = list

        self._filter.textChanged.connect(self._apply)

    def _apply(self, text):
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.applyFilter(text.lower())


class CopyDialog(QDialog):
    cellZonesCopied = Signal(set)

    def __init__(self, parent: QWidget, czid: str, mode: CopyMode):
        super().__init__(parent)
        self._ui = Ui_CopyDialog()
        self._ui.setupUi(self)

        self._sourceId: str = czid
        self._isRegionMode = False

        self._items: dict[str: CellZoneListItem] = {}
        self._copied: set[str] = set()

        self._targetFilter = Filter(self._ui.targetFilter, self._ui.targets)

        if mode == CopyMode.REGION:
            self._isRegionMode = True
            self.setWindowTitle(self.tr('Copy Region Conditions'))

        self._load()
        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.copy.clicked.connect(self._copy)
        self._ui.close.clicked.connect(self._close)

    def _load(self):
        source = CellZoneService.getCellZone(self._sourceId)
        self._ui.source.setText(source.rname if self._isRegionMode else source.scopedName)

        for cellZone in CellZoneService.getCellZones():
            if cellZone.isRegion() == self._isRegionMode and cellZone.czid != self._sourceId:
                self._items[cellZone.czid] = CellZoneListItem(self._ui.targets, cellZone)
    #
    # def _sourceChanged(self, item):
    #     if self._sourceId is not None:
    #         self._items[self._sourceId].setFlags(self._items[self._sourceId].flags() | Qt.ItemFlag.ItemIsEnabled)
    #
    #     self._sourceId = item.czid()
    #     self._items[self._sourceId].setFlags(self._items[self._sourceId].flags() & ~Qt.ItemFlag.ItemIsEnabled)

    @qasync.asyncSlot()
    async def _copy(self):
        targets = self._ui.targets.selectedItems()
        if not targets:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Targets'))
            return

        if not await AsyncMessageBox().confirm(
                self, self.tr('Copy Cell Zone Conditions'),
                self.tr('Copy {0} to ({1})?'.format(
                    self._ui.source.text(),
                    ', '.join([item.text() for item in targets])))):
            return

        for item in targets:
            self._copied.add(item.czid())
            copyCellZoneConditions(self._sourceId, item.czid())

    def _close(self):
        self.cellZonesCopied.emit(self._copied)
        self.close()
