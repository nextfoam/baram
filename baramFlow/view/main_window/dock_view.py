#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QMargins
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6QtAds import CDockManager, DockWidgetArea


class DockView(QWidget):
    # QtAds default colors inactive tab labels with palette(dark), which is
    # invisible against the dark window background in dark mode.
    _TAB_LABEL_OVERRIDE = '\nads--CDockWidgetTab QLabel { color: palette(placeholder-text); }'

    def __init__(self, menu):
        super().__init__()

        self._dockManager = CDockManager(self)
        self._baseStyleSheet = self._dockManager.styleSheet()
        self._applyTabLabelOverride()
        self._menu = menu

        layout = QVBoxLayout(self)
        layout.setContentsMargins(QMargins(0, 0, 0, 0))
        layout.addWidget(self._dockManager)

    def close(self):
        for dockWidget in self._dockManager.dockWidgets():
            dockWidget.widget().close()

        self._dockManager.deleteLater()

        super().close()

    def _applyTabLabelOverride(self):
        self._dockManager.setStyleSheet(self._baseStyleSheet + self._TAB_LABEL_OVERRIDE)

    def addDockWidget(self, dockWidget):
        self._dockManager.addDockWidgetTab(DockWidgetArea.CenterDockWidgetArea, dockWidget)
        # Re-apply the override so tabs added before this point are re-polished
        # alongside the new one — otherwise only the last-added tab picks it up.
        self._applyTabLabelOverride()
        self._menu.addAction(dockWidget.toggleViewAction())

    def removeDockWidget(self, dockWidget):
        self._menu.removeAction(dockWidget.toggleViewAction())
        self._dockManager.removeDockWidget(dockWidget)