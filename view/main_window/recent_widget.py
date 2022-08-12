#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from .recent_widget_ui import Ui_RecentWidget


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

        self._ui.remove.clicked.connect(self._remove)

    def getProjectPath(self):
        return self._ui.path.text()

    def _remove(self):
        self.removeClicked.emit(self)
