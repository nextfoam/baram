#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

from baramFlow.coredb.boundary_scaffold import BoundaryScaffold

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from widgets.selector_dialog import SelectorDialog

from .boundary_scaffold_dialog_ui import Ui_BoundaryScaffoldDialog


class BoundaryScaffoldDialog(QDialog):
    def __init__(self, parent, scaffold: BoundaryScaffold):
        super().__init__(parent)

        self._ui = Ui_BoundaryScaffoldDialog()
        self._ui.setupUi(self)

        self._scaffold = scaffold
        self._bcid = scaffold.bcid

        self._dialog = None

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))
        self._ui.name.setText(scaffold.name)

        if scaffold.bcid == '0':
            self._ui.boundary.setText('')
        else:
            bcname = BoundaryDB.getBoundaryText(scaffold.bcid)
            self._ui.boundary.setText(bcname)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectClicked)
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _selectClicked(self):
        if not self._dialog:
            boundaries = BoundaryDB.getBoundarySelectorItems()
            boundariesInUse = ScaffoldsDB().getBoundariesInUse()
            items = filter(lambda item: item.data not in boundariesInUse, boundaries)

            self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"), items)
            self._dialog.accepted.connect(self._boundarySelected)

        self._dialog.open()

    @qasync.asyncSlot()
    async def _boundarySelected(self):
        self._bcid = str(self._dialog.selectedItem())
        bcname = BoundaryDB.getBoundaryText(self._bcid)
        self._ui.boundary.setText(bcname)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._scaffold.name = self._ui.name.text()
        self._scaffold.bcid = self._bcid

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

        if self._bcid == '0':
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('One boundary should be selected.'))
            return False

        return True
