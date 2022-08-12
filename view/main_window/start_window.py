#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from enum import Enum, auto

import qasync

from PySide6.QtWidgets import QDialog, QListWidgetItem, QFileDialog, QMessageBox
from filelock import Timeout

from coredb.app_settings import AppSettings
from coredb.project_settings import ProjectSettings
from coredb.project import Project
from view.case_wizard.case_wizard import CaseWizard
from view.main_window.main_window import MainWindow, CloseType
from .start_window_ui import Ui_StartWindow
from .recent_widget import RecentWidget


RECENT_PROJECTS_NUMBER = 5


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
        self.pathItem = []

        self._setupRecentCases()

        self._connectSignalsSlots()

    def getProjectDirectory(self):
        return self._projectDirectory

    def _connectSignalsSlots(self):
        self._ui.newCase.clicked.connect(self._new)
        self._ui.open.clicked.connect(self._open)
        self._ui.recentCases.itemClicked.connect(self._openRecentProject)

    def _setupRecentCases(self):
        recentCases = AppSettings.getRecentProjects(RECENT_PROJECTS_NUMBER)
        self.pathItem = []

        for uuid_ in recentCases:
            settings = ProjectSettings()
            if settings.load(uuid_):
                self.pathItem.append(QListWidgetItem())
                widget = RecentWidget(settings)
                self.pathItem[-1].setSizeHint(widget.sizeHint())
                self._ui.recentCases.addItem(self.pathItem[-1])
                self._ui.recentCases.setItemWidget(self.pathItem[-1], widget)
                widget.removeClicked.connect(self._remove)

    def _remove(self, widget):
        path = widget.getProjectPath()
        total = self._ui.recentCases.count()
        selectedPos = -1

        for i in range(total):
            item = self._ui.recentCases.item(i)
            if widget == self._ui.recentCases.itemWidget(item):
                selectedPos = i

        msgBox = QMessageBox()
        msgBox.setWindowTitle(self.tr("Remove from list"))
        msgBox.setText(self.tr(f"Do you want to remove selected path from list?\n{path}"))
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msgBox.setDefaultButton(QMessageBox.Yes)

        result = msgBox.exec()
        if result == QMessageBox.Yes:
            self._ui.recentCases.takeItem(selectedPos)
            del self.pathItem[selectedPos]
            AppSettings.removeProject(selectedPos)
            # widget.deleteLater()

    def _new(self):
        self._dialog = CaseWizard(self)
        self._dialog.accepted.connect(self._createProject)
        self._dialog.open()

    def _open(self):
        self._dialog = QFileDialog(self, self.tr('Select Project Directory'), AppSettings.getRecentLocation())
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.accepted.connect(self._openExistingProject)
        self._dialog.open()

    def _openRecentProject(self, item):
        self._openProject(self._ui.recentCases.itemWidget(item).getProjectPath())

    def _createProject(self):
        directory = self._dialog.field('projectLocation')
        os.mkdir(directory)
        self._openProject(directory, True)

    def _openExistingProject(self):
        if dirs := self._dialog.selectedFiles():
            self._openProject(dirs[0])

    def _openProject(self, directory, create=False):
        try:
            Project.open(directory, create)
            self.done(QDialog.Accepted)

            return
        except FileNotFoundError:
            QMessageBox.critical(self._dialog, self.tr('Case Open Error'),
                                 self.tr(f'{os.path.basename(directory)} is not a baram case.'))
        except Timeout:
            QMessageBox.critical(self._dialog, self.tr('Case Open Error'),
                                 self.tr(f'{os.path.basename(directory)} is open in another program.'))

        Project.close()

class Baram:
    def __init__(self):
        self._toQuit = False
        self._dialog = None
        self._window = None
        self._applicationLock = None

    def toQuit(self):
        return self._toQuit

    async def start(self):
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

    @qasync.asyncSlot()
    async def _windowClosed(self, result):
        if result == CloseType.CLOSE_PROJECT:
            await self.start()
