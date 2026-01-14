#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

import asyncio

import qasync
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from .async_message_box import AsyncMessageBox
from .simple_sheet_dialog_ui import Ui_SimpleSheetDialog


class SimpleSheetDialog(QDialog):
    def __init__(self, parent, labels: list[str], data: Optional[list[list[float]]] = None, readOnly: bool = False):
        super().__init__(parent)

        self._ui = Ui_SimpleSheetDialog()
        self._ui.setupUi(self)

        self._ui.sheet.setup(labels, data, readOnly=readOnly)

        if readOnly:
            self._ui.cancel.hide()

        loop = asyncio.get_running_loop()
        self._future = loop.create_future()

        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    def show(self) -> asyncio.Future:

        super().show()

        return self._future

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not self._future.done():
            if not self._ui.sheet.isDataComplete():
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('Empty cells are not allowed within the data range.'))
                return

            data = self._ui.sheet.getData()
            self._future.set_result(data)

        self.close()

    def _cancelClicked(self):
        if not self._future.cancelled():
            self._future.cancel()

        self.close()

    def closeEvent(self, event):
        if not self._future.done():
            self._future.cancel()

        event.accept()
