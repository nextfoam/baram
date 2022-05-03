#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDockWidget


class TabifiedDock(QDockWidget):
    def __init__(self, mainWindow):
        super().__init__()
        self._mainWinow = mainWindow

        self._connectTabifySlots()

    def dockTopLevelChanged(self, topLevel):
        if not topLevel:
            self._mainWinow.tabifyDock(self)

    def dockToggled(self, checked):
        if checked:
            self.show()
            self.raise_()

    def _connectTabifySlots(self):
        self.topLevelChanged.connect(self.dockTopLevelChanged)
        self.toggleViewAction().toggled.connect(self.dockToggled)