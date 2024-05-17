#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PySide6.QtCore import QCoreApplication, QEvent, QMargins
from PySide6.QtGui import QFontDatabase

from PySide6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout
from PySide6QtAds import CDockWidget


class Console(QWidget):
    def __init__(self):
        super().__init__()
        self._view = QPlainTextEdit(self)

        charFormat = self._view.currentCharFormat()
        fixedFont = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        charFormat.setFont(fixedFont)
        self._view.setCurrentCharFormat(charFormat)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(QMargins(0, 0, 0, 0))
        layout.addWidget(self._view)

    def clear(self):
        self._view.clear()

    def append(self, text):
        self._view.appendPlainText(text)

    def appendError(self, text):
        self._view.appendPlainText(text)


class ConsoleView(CDockWidget):
    def __init__(self):
        super().__init__(self._title())

        self.setWidget(Console())

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.setWindowTitle(self._title())

        super().changeEvent(event)

    def clear(self):
        self.widget().clear()

    def _title(self):
        return QCoreApplication.translate('ConsoleView', 'Console')
