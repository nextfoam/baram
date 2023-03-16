#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from pathlib import Path

import qasync

from PySide6.QtCore import Qt, QObject
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from filelock import Timeout

from app import app
from coredb.app_settings import AppSettings
from coredb.project import Project, ProjectOpenType
from view.case_wizard.case_wizard import CaseWizard
from view.widgets.project_selector import ProjectSelector


logger = logging.getLogger(__name__)


class Baram(QObject):
    def __init__(self):
        super().__init__()

        self._projectSelector = None
        self._applicationLock = None
        app.closedForRestart.connect(self._restart)

    async def start(self):
        Project.close()

        try:
            self._applicationLock = AppSettings.acquireLock(5)
        except Timeout:
            return

        self._projectSelector = ProjectSelector()
        self._projectSelector.finished.connect(self._projectSelectorClosed, type=Qt.ConnectionType.QueuedConnection)
        self._projectSelector.actionNewSelected.connect(self._openCaseWizard)
        self._projectSelector.projectSelected.connect(self._openProject)
        self._projectSelector.open()

    def _projectSelectorClosed(self, result):
        self._applicationLock.release()

        if result == QDialog.Rejected:
            QApplication.quit()

    def _openCaseWizard(self):
        self._caseWizard = CaseWizard(self._projectSelector)
        self._caseWizard.accepted.connect(self._createCaseFromWizard)
        self._caseWizard.open()

    def _createCaseFromWizard(self):
        path = Path(self._caseWizard.field('projectLocation'))
        path.mkdir()
        self._openProject(path, ProjectOpenType.WIZARD)

    @qasync.asyncSlot()
    async def _restart(self):
        Project.close()
        await self.start()

    def _openProject(self, directory, openType=ProjectOpenType.EXISTING):
        try:
            path = Path(directory)

            Project.open(path, openType)
            self._projectSelector.accept()

            app.projectPrepared.emit()

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
        return False
