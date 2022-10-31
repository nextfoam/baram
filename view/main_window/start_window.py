#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from enum import Enum, auto

import qasync

from PySide6.QtCore import Qt, QRect
from PySide6.QtWidgets import QApplication, QDialog, QListWidgetItem, QFileDialog, QMessageBox
from PySide6.QtGui import QIcon

from filelock import Timeout

from app import app
from coredb.app_settings import AppSettings
from coredb.project_settings import ProjectSettings
from coredb.project import Project, ProjectOpenType
from coredb import coredb
from resources import resource
from view.case_wizard.case_wizard import CaseWizard
from view.main_window.main_window import MainWindow, CloseType
from .start_window_ui import Ui_StartWindow
from .recent_widget import RecentWidget


logger = logging.getLogger(__name__)

RECENT_PROJECTS_NUMBER = 100


class StartAction(Enum):
    ACTION_NEW = 0
    ACTION_OPEN = auto()


class StartWindow(QDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_StartWindow()
        self._ui.setupUi(self)

        self.setWindowIcon(QIcon(str(resource.file('baram.ico'))))

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
        coredb.createDB()
        self._dialog = CaseWizard(self)
        self._dialog.finished.connect(self._createProject)
        self._dialog.open()

    def _open(self):
        self._dialog = QFileDialog(self, self.tr('Select Project Directory'), AppSettings.getRecentLocation())
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.accepted.connect(self._openExistingProject)
        self._dialog.open()

    def _openRecentProject(self, item):
        self._openProject(self._ui.recentCases.itemWidget(item).getProjectPath())

    def _createProject(self, result):
        if result == QDialog.Accepted:
            directory = self._dialog.field('projectLocation')
            os.mkdir(directory)
            self._openProject(directory, ProjectOpenType.WIZARD)
        else:
            coredb.destroy()

    def _openExistingProject(self):
        if dirs := self._dialog.selectedFiles():
            self._openProject(dirs[0])

    def _openProject(self, directory, openType=ProjectOpenType.EXISTING):
        try:
            Project.open(directory, openType)
            self.done(QDialog.Accepted)

            return
        except FileNotFoundError:
            QMessageBox.critical(self._dialog, self.tr('Case Open Error'),
                                 self.tr(f'{os.path.basename(directory)} is not a baram case.'))
        except Timeout:
            QMessageBox.critical(self._dialog, self.tr('Case Open Error'),
                                 self.tr(f'{os.path.basename(directory)} is open in another program.'))
        except Exception as ex:
            logger.info(ex, exc_info=True)
            QMessageBox.critical(self._dialog, self.tr('Case Open Error'),
                                 self.tr('Fail to open case\n' + str(ex)))

        Project.close()


class Baram:
    def __init__(self):
        self._toQuit = False
        self._dialog = None
        self._applicationLock = None

    def toQuit(self):
        return self._toQuit

    async def start(self):
        try:
            self._applicationLock = AppSettings.acquireLock(5)
        except Timeout:
            return

        self._dialog = StartWindow()
        self._dialog.finished.connect(self._starterClosed, type=Qt.ConnectionType.QueuedConnection)
        rect = AppSettings.getLastStartWindowPosition()
        self._dialog.setGeometry(QRect(rect[0], rect[1], rect[2], rect[3]))
        self._dialog.open()

    def _starterClosed(self, result):
        self._applicationLock.release()

        rect = self._dialog.geometry()
        getRect = [rect.x(), rect.y(), rect.width(), rect.height()]
        AppSettings.updateLastStartWindowPosition(getRect)

        if result == QDialog.Accepted:
            app.setMainWindow(MainWindow())
            app.window.windowClosed.connect(self._windowClosed, type=Qt.ConnectionType.QueuedConnection)

            rect = AppSettings.getLastMainWindowPosition()
            app.window.setGeometry(QRect(rect[0], rect[1], rect[2], rect[3]))
        else:
            QApplication.quit()

    @qasync.asyncSlot()
    async def _windowClosed(self, result):
        rect = app.window.geometry()
        getRect = [rect.x(), rect.y(), rect.width(), rect.height()]
        AppSettings.updateLastMainWindowPosition(getRect)
        Project.close()

        if result == CloseType.CLOSE_PROJECT:
            await self.start()
        else:
            QApplication.quit()
