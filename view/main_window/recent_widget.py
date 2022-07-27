#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from PySide6.QtWidgets import QWidget

from coredb.project_settings import ProjectSettingKey
from .recent_widget_ui import Ui_RecentWidget


class RecentWidget(QWidget):
    def __init__(self, settings):
        super().__init__()
        self._ui = Ui_RecentWidget()
        self._ui.setupUi(self)

        fullPath = settings[ProjectSettingKey.CASE_FULL_PATH.value]
        self._ui.name.setText(os.path.basename(fullPath))
        self._ui.status.setText('configuring')
        self._ui.path.setText(fullPath)

    def getProjectPath(self):
        return self._ui.path.text()
