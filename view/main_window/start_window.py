#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from enum import Enum, auto

from PySide6.QtWidgets import QDialog, QListWidgetItem, QFileDialog, QMessageBox
from PySide6.QtCore import Signal

from coredb.settings import Settings
from coredb.project_settings import ProjectSettings
from coredb.project import Project
from coredb.filedb import FileDB
from view.case_wizard.case_wizard import CaseWizard
from view.main_window.main_window import MainWindow
from .start_window_ui import Ui_StartWindow
from .recent_widget import RecentWidget


class GlobalSettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    DISPLAY_SCALE = 'display_scale'
    RECENT_DIRECTORY = 'recent_directory'
    RECENT_CASES = 'recent_cases'


class StartAction(Enum):
    ACTION_NEW = 0
    ACTION_OPEN = auto()


class StartWindow(QDialog):
    projectSelected = Signal(StartAction, str)

    def __init__(self):
        super().__init__()
        self._ui = Ui_StartWindow()
        self._ui.setupUi(self)

        self._dialog = None
        self._projectDirectory = None

        self._setupRecentCases()

        self._connectSignalsSlots()

    def getProjectDirectory(self):
        return self._projectDirectory

    def _connectSignalsSlots(self):
        self._ui.newCase.clicked.connect(self._new)
        self._ui.open.clicked.connect(self._open)
        self._ui.recentCases.itemClicked.connect(self._openRecentCase)

    def _setupRecentCases(self):
        recentCases = Settings.getRecentCases()
        for projectId in recentCases:
            settings = ProjectSettings.loadSettings(projectId)
            if settings:
                item = QListWidgetItem()
                widget = RecentWidget(settings)
                item.setSizeHint(widget.sizeHint())
                self._ui.recentCases.addItem(item)
                self._ui.recentCases.setItemWidget(item, widget)

    def _new(self):
        self._dialog = CaseWizard(self)
        self._dialog.accepted.connect(self._createProject)
        self._dialog.open()

    def _open(self):
        dirName = QFileDialog.getExistingDirectory(self, self.tr('Project Directory'), Settings.getRecentDirectory())
        if dirName:
            self.projectSelected.emit(StartAction.ACTION_OPEN, dirName)

    def _openRecentCase(self, item):
        self.projectSelected.emit(StartAction.ACTION_OPEN, self._ui.recentCases.itemWidget(item).getProjectPath())

    def _createProject(self):
        directory = self._dialog.field('projectLocation')
        os.mkdir(directory)
        self.projectSelected.emit(StartAction.ACTION_NEW, directory)


class Baram:
    def __init__(self):
        self._toQuit = False
        self._dialog = None
        self._window = None
        self._applicationLock = None
        self._projectSettings = None
        Settings.init()

    def toQuit(self):
        return self._toQuit

    def start(self):
        if self._window and self._window.toQuit():
            return False

        self._applicationLock = Settings.acquireLock(5)
        if self._applicationLock:
            self._dialog = StartWindow()
            self._dialog.projectSelected.connect(self._startMainWindow)
            self._dialog.finished.connect(self._starterClosed)
            self._dialog.open()
            return True

        return False

    def _starterClosed(self, result):
        self._applicationLock.release()
        self._toQuit = result == QDialog.Rejected

    def _startMainWindow(self, action, directory):
        project = Project.open(directory)
        if action == StartAction.ACTION_OPEN and project.uuid is None:
            QMessageBox.critical(self._dialog, self._dialog.tr('Case Open Error'),
                                 self._dialog.tr(f'{os.path.basename(directory)} is not a baram case.'))
            return

        self._projectSettings = ProjectSettings(project)

        if not self._projectSettings.acquireLock(5):
            QMessageBox.critical(self._dialog, self._dialog.tr('Case Open Error'),
                                 self._dialog.tr(f'{project.name} is open in another program.'))
            return

        Settings.updateRecents(project, action == StartAction.ACTION_NEW)
        self._dialog.done(QDialog.Accepted)
        self._applicationLock.release()

        FileDB.initFilePath(directory)
        FileDB.load()

        self._window = MainWindow(project)
        self._window.windowClosed.connect(self._windowClosed)

    def _windowClosed(self):
        self._projectSettings.releaseLock()
