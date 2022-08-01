#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from enum import Enum, auto

from PySide6.QtWidgets import QDialog, QListWidgetItem, QFileDialog, QMessageBox
from filelock import Timeout

from coredb.app_settings import AppSettings
from coredb.project_settings import ProjectSettings
from coredb.project import Project
from view.case_wizard.case_wizard import CaseWizard
from view.main_window.main_window import MainWindow, CloseType
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
        recentCases = AppSettings.getRecentCases()
        for uuid_ in recentCases:
            settings = ProjectSettings()
            if settings.load(uuid_):
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
        dirName = QFileDialog.getExistingDirectory(self, self.tr('Project Directory'), AppSettings.getRecentDirectory())
        if dirName:
            self._openProject(dirName)

    def _openRecentCase(self, item):
        self._openProject(self._ui.recentCases.itemWidget(item).getProjectPath())

    def _createProject(self):
        directory = self._dialog.field('projectLocation')
        os.mkdir(directory)
        self._openProject(directory, True)

    def _openProject(self, directory, create=False):
        try:
            Project.open(directory, create)
            self.done(QDialog.Accepted)
        except FileNotFoundError:
            QMessageBox.critical(self._dialog, self._dialog.tr('Case Open Error'),
                                 self._dialog.tr(f'{os.path.basename(directory)} is not a baram case.'))
        except Timeout:
            QMessageBox.critical(self._dialog, self._dialog.tr('Case Open Error'),
                                 self._dialog.tr(f'{os.path.basename(directory)} is open in another program.'))


class Baram:
    def __init__(self):
        self._toQuit = False
        self._dialog = None
        self._window = None
        self._applicationLock = None

    def toQuit(self):
        return self._toQuit

    def start(self):
        try:
            self._applicationLock = AppSettings.acquireLock(5)
        except Timeout:
            return

        self._dialog = StartWindow()
        self._dialog.finished.connect(self._starterClosed)
        self._dialog.open()

    def _starterClosed(self, result):
        self._applicationLock.release()
        if result == QDialog.Accepted:
            self._window = MainWindow()
            self._window.windowClosed.connect(self._windowClosed)

    def _windowClosed(self, result):
        if result == CloseType.CLOSE_PROJECT:
            self.start()
