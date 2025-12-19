#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QListWidgetItem

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from .copy_dialog_ui import Ui_CopyDialog


class BoundaryListItem(QListWidgetItem):
    def __init__(self, parent, bcid, bcname, rname):
        super().__init__(parent)

        self._bcid = bcid
        self._textForFiltering: str = bcname.lower()

        prefix = '' if rname == '' else rname + ':'
        self.setText(prefix + bcname)

    def bcid(self):
        return self._bcid

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
    boundariesCopied = Signal(set)

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_CopyDialog()
        self._ui.setupUi(self)

        self._items = {}
        self._sourceId = bcid
        self._copied = set()

        self._sourceFilter = Filter(self._ui.sourceFilter, self._ui.source)
        self._targetFilter = Filter(self._ui.targetFilter, self._ui.targets)

        self._load()
        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.source.itemClicked.connect(self._sourceChanged)
        self._ui.copy.clicked.connect(self._copy)
        self._ui.close.clicked.connect(self._close)

    def _load(self):
        db = coredb.CoreDB()
        for rname in db.getRegions():
            for bcid, bcname, bctype in db.getBoundaryConditions(rname):
                self._items[bcid] = BoundaryListItem(self._ui.targets, bcid, bcname, rname)

                if not BoundaryDB.needsCoupledBoundary(BoundaryType(bctype)):
                    item = BoundaryListItem(self._ui.source, bcid, bcname, rname)

                    if bcid == self._sourceId:
                        item.setSelected(True)
                        self._items[bcid].setFlags(self._items[bcid].flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)

    def _sourceChanged(self, item):
        if self._sourceId is not None:
            self._items[self._sourceId].setFlags(self._items[self._sourceId].flags() | Qt.ItemFlag.ItemIsEnabled)

        self._sourceId = item.bcid()
        self._items[self._sourceId].setFlags(self._items[self._sourceId].flags() & ~Qt.ItemFlag.ItemIsEnabled)

    @qasync.asyncSlot()
    async def _copy(self):
        targets = self._ui.targets.selectedItems()
        if not targets:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Target Boundaries'))
            return

        if not await AsyncMessageBox().confirm(
                self, self.tr('Copy Boundary Conditions'),
                self.tr('Copy {} to ({})?'.format(
                    self._ui.source.selectedItems()[0].text(),
                    ', '.join([item.text() for item in self._ui.targets.selectedItems()])))):
            return

        for item in targets:
            self._copied.add(item.bcid())
            db = coredb.CoreDB()
            db.copyBoundaryConditions(self._sourceId, item.bcid())

    def _close(self):
        self.boundariesCopied.emit(self._copied)
        self.close()
