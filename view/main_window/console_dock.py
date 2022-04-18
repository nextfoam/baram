#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QVBoxLayout, QWidget, QTextBrowser
from PySide6.QtCore import Qt

from .tabified_dock import TabifiedDock


class ConsoleDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._textView = None
        self._setup()

    def _setup(self):
        self.setWindowTitle(self.tr("Console"))
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self._dockWidgetContents = QWidget()
        self._layout = QVBoxLayout(self._dockWidgetContents)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._textView = QTextBrowser()
        self._layout.addWidget(self._textView)
        self.setWidget(self._dockWidgetContents)

