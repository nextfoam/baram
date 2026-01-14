#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QLineEdit

from widgets.new_project_widget import NewProjectWidget

from baramFlow.app import app
from baramFlow.coredb.app_settings import AppSettings


class WorkspacePage(QWizardPage):
    def __init__(self, parent, path=None):
        super(WorkspacePage, self).__init__(parent)

        self._widget = None
        self._projectPath = QLineEdit()

        self._complete = False

        if path is None:
            self._widget = NewProjectWidget(self, Path(AppSettings.getRecentLocation()).resolve(),
                                            app.properties.projectSuffix)
        else:
            self._widget = NewProjectWidget(self)
            self._widget.setFixedProjectPath(path)
            self._projectPath.setText(str(path))

        layout = QVBoxLayout(self)
        layout.addWidget(self._widget)
        layout.addWidget(self._projectPath)
        layout.addStretch()

        self._projectPath.hide()

        self.registerField('projectPath*', self._projectPath)

        self._dialog = None

        self._connectSignalsSlots()

    def isComplete(self):
        complete = len(self._projectPath.text()) > 0

        if complete != self._complete:
            self._complete = complete
            self.completeChanged.emit()

        return complete

    def _connectSignalsSlots(self):
        self._widget.pathChanged.connect(self._updateProjectPath)

    def _updateProjectPath(self, path):
        if path is None:
            self._projectPath.clear()
        else:
            self._projectPath.setText(str(path))
