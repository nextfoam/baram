#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QMargins
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6QtAds import CDockManager, DockWidgetArea


class DockView(QWidget):
    def __init__(self, menu):
        super().__init__()

        self._dockManager = CDockManager(self)
        self._menu = menu

        layout = QVBoxLayout(self)
        layout.setContentsMargins(QMargins(0, 0, 0, 0))
        layout.addWidget(self._dockManager)

    def close(self):
        for dockWidget in self._dockManager.dockWidgets():
            dockWidget.widget().close()

        self._dockManager.deleteLater()

        super().close()

    def addDockWidget(self, dockWidget):
        self._dockManager.addDockWidgetTab(DockWidgetArea.CenterDockWidgetArea, dockWidget)
        self._menu.addAction(dockWidget.toggleViewAction())

    def removeDockWidget(self, dockWidget):
        self._menu.removeAction(dockWidget.toggleViewAction())
        self._dockManager.removeDockWidget(dockWidget)