#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

from baramFlow.base.scaffold.boundary_scaffold import BoundaryScaffold

from baramFlow.view.widgets.multi_selector_dialog import MultiSelectorDialog
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB

from .boundary_scaffold_dialog_ui import Ui_BoundaryScaffoldDialog


class BoundaryScaffoldDialog(QDialog):
    def __init__(self, parent, scaffold: BoundaryScaffold):
        super().__init__(parent)

        self._ui = Ui_BoundaryScaffoldDialog()
        self._ui.setupUi(self)

        self._scaffold = scaffold
        self._boundaries = scaffold.boundaries

        self._dialog = None

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))
        self._ui.name.setText(scaffold.name)

        self._setBoundaries(self._boundaries)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectClicked)
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _selectClicked(self):
        boundaries = BoundaryDB.getBoundarySelectorItems()
        self._dialog = MultiSelectorDialog(self, self.tr("Select Boundaries"), boundaries, self._boundaries)
        self._dialog.accepted.connect(self._boundariesChanged)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _boundariesChanged(self):
        boundaries: list[str] = self._dialog.selectedItems()
        self._setBoundaries(boundaries)

    def _setBoundaries(self, boundaries):
        self._boundaries = boundaries

        self._ui.boundaries.clear()
        for bcid in boundaries:
            self._ui.boundaries.addItem(BoundaryDB.getBoundaryText(bcid))

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._scaffold.name = self._ui.name.text()
        self._scaffold.boundaries = self._boundaries

        self.accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        self.reject()

    async def _valid(self) -> bool:
        name = self._ui.name.text()
        if ScaffoldsDB().nameDuplicates(self._scaffold.uuid, name):
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Surface Name already exists.'))
            return False

        if len(self._boundaries) == 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('One boundary should be selected.'))
            return False

        return True
