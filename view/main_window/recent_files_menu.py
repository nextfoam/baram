#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtCore import QObject, Signal


MAX_COUNT = 50


class RecentFilesMenu(QObject):
    projectSelected = Signal(str)

    def __init__(self, root):
        super().__init__()
        self._root = root
        self._actions = None
        self._recentest = None

    def setRecents(self, paths):
        self._root.clear()
        self._actions = {}

        if paths:
            for i in range(min(MAX_COUNT, len(paths))):
                path = Path(paths[i])
                action = self._newAction(path)
                self._root.addAction(action)

            self._recentest = self._actions[Path(paths[0])]

    def addRecentest(self, path):
        action = self._newAction(path)
        self._root.insertAction(self._recentest, action)
        self._recentest = action

    def updateRecentest(self, path):
        action = self._actions[path] if path in self._actions else None
        if action == self._recentest:
            return

        if action:
            self._root.removeAction(action)
            self._root.insertAction(self._recentest, action)
            self._recentest = action
        else:
            self.addRecentest(path)

    def _recentTriggered(self):
        self.projectSelected.emit(str(self.sender().data()))

    def _newAction(self, path):
        action = QAction(path.name)
        action.setData(path)
        action.triggered.connect(self._recentTriggered)
        self._actions[path] = action

        return action

