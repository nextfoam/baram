#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject

from PySide6.QtWidgets import QPlainTextEdit


class ConsoleView(QObject):
    def __init__(self, ui):
        super().__init__()
        self._view:QPlainTextEdit = ui.console

    def clear(self):
        self._view.clear()

    def append(self, text):
        self._view.appendPlainText(text)

    def appendError(self, text):
        self._view.appendPlainText(text)
