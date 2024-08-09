#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QListWidgetItem

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from .copy_dialog_ui import Ui_CopyDialog


class CopyDialog(QDialog):
    boundariesCopied = Signal(set)

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_CopyDialog()
        self._ui.setupUi(self)

        self._items = {}
        self._sourceId = None
        self._copied = set()

        self._load()
        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.source.itemClicked.connect(self._sourceChanged)
        self._ui.copy.clicked.connect(self._copy)
        self._ui.close.clicked.connect(self._close)

    def _load(self):
        db = coredb.CoreDB()
        for rname in db.getRegions():
            r = '' if rname == '' else rname + ':'
            for bcid, bcname, bctype in db.getBoundaryConditions(rname):
                label = r + bcname
                if not BoundaryDB.needsCoupledBoundary(bctype):
                    QListWidgetItem(label, self._ui.source, bcid)
                self._items[bcid] = QListWidgetItem(label, self._ui.targets, bcid)

    def _sourceChanged(self, item):
        if self._sourceId is not None:
            self._items[self._sourceId].setFlags(self._items[self._sourceId].flags() | Qt.ItemFlag.ItemIsEnabled)

        self._sourceId = item.type()
        self._items[self._sourceId].setFlags(self._items[self._sourceId].flags() & ~Qt.ItemFlag.ItemIsEnabled)

    @qasync.asyncSlot()
    async def _copy(self):
        if not await AsyncMessageBox().confirm(
                self, self.tr('Copy Bonudary Conditions'),
                self.tr('Copy {} to ({})?'.format(
                    self._ui.source.currentItem().text(),
                    ', '.join([item.text() for item in self._ui.targets.selectedItems()])))):
            return

        for item in self._ui.targets.selectedItems():
            self._copied.add(item.type())
            db = coredb.CoreDB()
            db.copyBoundaryConditions(self._sourceId, item.type())

    def _close(self):
        self.boundariesCopied.emit(self._copied)
        self.close()
