#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDockWidget
from PySide6.QtCore import QEvent


class TabifiedDock(QDockWidget):
    def __init__(self, mainWindow):
        super().__init__()
        self._mainWindow = mainWindow

        self._connectTabifySlots()

    def _dockTopLevelChanged(self, topLevel):
        if not topLevel:
            self._mainWindow.tabifyDock(self)

    def _dockToggled(self, checked):
        if checked:
            self.show()
            self.raise_()

    def _connectTabifySlots(self):
        self.topLevelChanged.connect(self._dockTopLevelChanged)
        self.toggleViewAction().toggled.connect(self._dockToggled)

    def _translate(self):
        return

    def changeEvent(self, event):
        if event.type() == QEvent.LanguageChange:
            self._translate()

        super().changeEvent(event)
