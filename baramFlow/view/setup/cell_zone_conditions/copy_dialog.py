#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from enum import Enum, auto

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QListWidgetItem

from baramFlow.coredb.cell_zone_db import CellZoneDB, copyCellZoneConditions
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from .copy_dialog_ui import Ui_CopyDialog


class CopyMode(Enum):
    REGION = auto()
    CELL_ZONE = auto()


class CellZoneListItem(QListWidgetItem):
    def __init__(self, parent, czid, czname, rname):
        super().__init__(parent)

        self._czid = czid
        self._textForFiltering: str = ''

        if CellZoneDB.isRegion(czname):
            if not rname:
                rname = DEFAULT_REGION_NAME
            self._textForFiltering = rname.lower()
            self.setText(rname)
        else:
            self._textForFiltering = czname.lower()
            prefix = '' if rname == '' else rname + ':'
            self.setText(prefix + czname)

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

    def __init__(self, parent, czid, mode):
        super().__init__(parent)
        self._ui = Ui_CopyDialog()
        self._ui.setupUi(self)

        self._sourceId = czid
        self._isRegionMode = False

        self._items = {}
        self._copied = set()

        self._sourceFilter = Filter(self._ui.sourceFilter, self._ui.source)
        self._targetFilter = Filter(self._ui.targetFilter, self._ui.targets)

        if mode == CopyMode.REGION:
            self._isRegionMode = True
            self.setWindowTitle(self.tr('Copy Region Conditions'))

        self._load()
        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.source.itemClicked.connect(self._sourceChanged)
        self._ui.copy.clicked.connect(self._copy)
        self._ui.close.clicked.connect(self._close)

    def _load(self):
        db = coredb.CoreDB()
        for rname in db.getRegions():
            for czid, czname in db.getCellZones(rname):
                if CellZoneDB.isRegion(czname) == self._isRegionMode:
                    item = CellZoneListItem(self._ui.source, czid, czname, rname)
                    self._items[czid] = CellZoneListItem(self._ui.targets, czid, czname, rname)

                    if czid == self._sourceId:
                        item.setSelected(True)
                        self._items[czid].setFlags(self._items[czid].flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)

    def _sourceChanged(self, item):
        if self._sourceId is not None:
            self._items[self._sourceId].setFlags(self._items[self._sourceId].flags() | Qt.ItemFlag.ItemIsEnabled)

        self._sourceId = item.czid()
        self._items[self._sourceId].setFlags(self._items[self._sourceId].flags() & ~Qt.ItemFlag.ItemIsEnabled)

    @qasync.asyncSlot()
    async def _copy(self):
        targets = self._ui.targets.selectedItems()
        if not targets:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Targets'))
            return

        if not await AsyncMessageBox().confirm(
                self, self.tr('Copy Cell Zone Conditions'),
                self.tr('Copy {} to ({})?'.format(
                    self._ui.source.selectedItems()[0].text(),
                    ', '.join([item.text() for item in targets])))):
            return

        for item in targets:
            self._copied.add(item.czid())
            copyCellZoneConditions(self._sourceId, item.czid())

    def _close(self):
        self.cellZonesCopied.emit(self._copied)
        self.close()
