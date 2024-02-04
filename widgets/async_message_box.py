#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox


class AsyncMessageBox:
    _messageBoxes = set()  # To keep "AsyncQMessageBox" objects created at the same line with "await"

    def __init__(self):
        self._future = None
        self._mbox = None

    def critical(self, parent, title, text, buttons=QMessageBox.StandardButton.Ok,
                 defaultButton=QMessageBox.StandardButton.NoButton):
        return self._showMessageBox(parent, QMessageBox.Icon.Critical, title, text,
                                    buttons=buttons, defaultButton=defaultButton)

    def information(self, parent, title, text, buttons=QMessageBox.StandardButton.Ok,
                    defaultButton=QMessageBox.StandardButton.NoButton):
        return self._showMessageBox(parent, QMessageBox.Icon.Information, title, text,
                                    buttons=buttons, defaultButton=defaultButton)

    def question(self, parent, title, text, buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                 defaultButton=QMessageBox.StandardButton.NoButton):
        return self._showMessageBox(parent, QMessageBox.Icon.Question, title, text,
                                    buttons=buttons, defaultButton=defaultButton)

    def warning(self, parent, title, text, buttons=QMessageBox.StandardButton.Ok,
                defaultButton=QMessageBox.StandardButton.NoButton):
        return self._showMessageBox(parent, QMessageBox.Icon.Warning, title, text,
                                    buttons=buttons, defaultButton=defaultButton)

    def _showMessageBox(self, parent, icon, title, text, buttons, defaultButton):
        self._messageBoxes.add(self)

        loop = asyncio.get_running_loop()
        self._future = loop.create_future()

        self._mbox = QMessageBox(icon, title, text, buttons=buttons, parent=parent)
        self._mbox.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._mbox.finished.connect(self._finished)

        if defaultButton != QMessageBox.StandardButton.NoButton:
            self._mbox.setDefaultButton(defaultButton)

        self._mbox.show()

        return self._future

    def _finished(self, result: int):
        if not self._future.cancelled():
            self._future.set_result(result)

        self._messageBoxes.discard(self)
