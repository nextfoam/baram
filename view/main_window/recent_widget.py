#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from pathlib import Path

# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from .recent_widget_ui import Ui_RecentWidget


# class WatchDogEvent(FileSystemEventHandler):
#     def __init__(self, path):
#         self._path = path
#
#     def on_moved(self, event):
#         print("on_moved")
#
#     def on_modified(self, event):
#         print("on_modified")
#
#     def on_deleted(self, event):
#         print("on_deleted")
#
#     def on_created(self, event):
#         print("on_created")

class RecentWidget(QWidget):
    removeClicked = Signal(QWidget)

    def __init__(self, settings):
        super().__init__()
        self._ui = Ui_RecentWidget()
        self._ui.setupUi(self)

        path = settings.path
        self._ui.name.setText(os.path.basename(path))
        if settings.getProcess():
            self._ui.status.setText('Running')

        self._ui.path.setText(path)

        if not os.path.isdir(path):
            self._ui.path.setDisabled(True)
            self._ui.name.setDisabled(True)

        # self.watchPath = Observer()
        # self.eventWatch = WatchDogEvent(path)
        # checkPath = str(Path(path).parent)
        # self.watchPath.schedule(self.eventWatch, checkPath, recursive=True)
        # self.watchPath.start()

        self._ui.remove.clicked.connect(self._remove)

    def getProjectPath(self):
        return self._ui.path.text()

    def _remove(self):
        self.removeClicked.emit(self)
        # self.watchPath.stop()



