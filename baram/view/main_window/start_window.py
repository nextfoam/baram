#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from pathlib import Path

import qasync

from PySide6.QtCore import Qt, QObject
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from filelock import Timeout

from baram.app import app
from baram.coredb.app_settings import AppSettings
from baram.coredb.project import Project, ProjectOpenType
from baram.view.widgets.project_selector import ProjectSelector


logger = logging.getLogger(__name__)


class Baram(QObject):
    def __init__(self):
        super().__init__()

        self._projectSelector = None
        self._applicationLock = None

        app.restarted.connect(self._restart)
        app.projectCreated.connect(self._openNewProject)

    async def start(self):
        try:
            self._applicationLock = AppSettings.acquireLock(5)
        except Timeout:
            return

        self._projectSelector = ProjectSelector()
        self._projectSelector.finished.connect(self._projectSelectorClosed, type=Qt.ConnectionType.QueuedConnection)
        self._projectSelector.actionNewSelected.connect(self._createProject)
        self._projectSelector.projectSelected.connect(self._openExistingProject)
        self._projectSelector.open()

    def _createProject(self):
        app.plug.createProject(self._projectSelector)

    def _projectSelectorClosed(self, result):
        self._applicationLock.release()

        if result == QDialog.DialogCode.Rejected:
            QApplication.quit()

    @qasync.asyncSlot()
    async def _restart(self):
        Project.close()
        await self.start()

    def _openExistingProject(self, directory):
        self._openProject(Path(directory), ProjectOpenType.EXISTING)

    def _openNewProject(self, path):
        self._openProject(path, ProjectOpenType.NEW)

    def _openProject(self, path, openType):
        try:
            Project.open(path.resolve(), openType)
            self._projectSelector.accept()  # To close project selector dialog
            app.openMainWindow()

            return
        except FileNotFoundError:
            QMessageBox.critical(self._projectSelector, self.tr('Case Open Error'),
                                 self.tr(f'{path.name} is not a baram case.'))
        except Timeout:
            QMessageBox.critical(self._projectSelector, self.tr('Case Open Error'),
                                 self.tr(f'{path.name} is open in another program.'))
        except Exception as ex:
            QMessageBox.critical(self._projectSelector, self.tr('Case Open Error'),
                                 self.tr('Fail to open case\n' + str(ex)))

        Project.close()
