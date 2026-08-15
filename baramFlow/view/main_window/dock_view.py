#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QMargins
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6QtAds import (CDockManager, DockWidgetArea, TitleBarButtonClose, TitleBarButtonTabsMenu,
                           TitleBarButtonUndock)


class DockView(QWidget):
    # QtAds default colors inactive tab labels with palette(dark), which is
    # invisible against the dark window background in dark mode.
    _TAB_LABEL_OVERRIDE = '\nads--CDockWidgetTab QLabel { color: palette(placeholder-text); }'

    def __init__(self, menu):
        super().__init__()

        CDockManager.setConfigFlag(CDockManager.eConfigFlag.UseNativeWindows, True)

        self._dockManager = CDockManager(self)
        self._baseStyleSheet = self._dockManager.styleSheet()
        self._applyTabLabelOverride()
        self._menu = menu

        layout = QVBoxLayout(self)
        layout.setContentsMargins(QMargins(8, 0, 0, 0))
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

    def setTabSwitchingEnabled(self, enabled: bool):
        # A floated dock widget drops out of self._dockManager.dockWidgets() and
        # gets its own separate dock area, so both have to be walked explicitly —
        # otherwise a floated report's own tab/title-bar (or another report's, if
        # the wrong area gets picked as "the" shared one) is left unlocked.
        dockWidgets = list(self._dockManager.dockWidgets())
        for floatingContainer in self._dockManager.floatingWidgets():
            dockWidgets.extend(floatingContainer.dockWidgets())

        if not dockWidgets:
            return

        # Every tab is disabled, including the active one — otherwise it can still
        # be dragged out of the main window into a floating window.
        areas = set()
        for dockWidget in dockWidgets:
            tab = dockWidget.tabWidget()
            if tab is not None:
                tab.setEnabled(enabled)

            area = dockWidget.dockAreaWidget()
            if area is not None:
                areas.add(area)

        # Each area's title bar operations (tab list menu, undock, close) act on
        # whichever dock is currently active in that area and bypass the per-tab
        # disable above.
        for area in areas:
            for button in (TitleBarButtonTabsMenu, TitleBarButtonUndock, TitleBarButtonClose):
                titleBarButton = area.titleBarButton(button)
                if titleBarButton is not None:
                    titleBarButton.setEnabled(enabled)