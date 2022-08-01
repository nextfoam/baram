#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from PySide6.QtWidgets import QWidget

from .recent_widget_ui import Ui_RecentWidget


class RecentWidget(QWidget):
    def __init__(self, settings):
        super().__init__()
        self._ui = Ui_RecentWidget()
        self._ui.setupUi(self)

        fullPath = settings.projectPath
        self._ui.name.setText(os.path.basename(fullPath))
        if settings.getProcess():
            self._ui.status.setText('Running')
        self._ui.path.setText(fullPath)

    def getProjectPath(self):
        return self._ui.path.text()
