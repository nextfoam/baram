#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import ctypes
import logging
import platform
from pathlib import Path

import qasync

from filelock import Timeout

from PySide6.QtCore import Qt, QObject
from PySide6.QtWidgets import QApplication, QDialog

from libbaram.openfoam.constants import isBaramProject
from widgets.async_message_box import AsyncMessageBox
from libbaram import vtk_threads

from baramFlow.app import app
from baramFlow.coredb.app_settings import AppSettings
from baramFlow.coredb.filedb import FileDB
from baramFlow.coredb.project import Project, ProjectOpenType
from baramFlow.view.widgets.project_selector import ProjectSelector


logger = logging.getLogger(__name__)


class Baram(QObject):
    def __init__(self):
        super().__init__()

        self._projectSelector = None
        self._applicationLock = None

        app.restarted.connect(self._restart)
        app.projectCreated.connect(self._openProject)

    async def start(self, path=None):
        vtk_threads.vtkThreadLock = asyncio.Lock()

        if path is not None:
            await self._projectSelected(path)

            return

        try:
            self._applicationLock = AppSettings.acquireLock(5)
        except Timeout:
            return

        self._projectSelector = ProjectSelector()
        self._projectSelector.finished.connect(self._projectSelectorClosed, type=Qt.ConnectionType.QueuedConnection)
        self._projectSelector.actionNewSelected.connect(self._createProject)
        self._projectSelector.projectSelected.connect(self._projectSelected)
        self._projectSelector.open()

    def _projectSelectorClosed(self, result):
        self._applicationLock.release()

        if result == QDialog.DialogCode.Rejected:
            QApplication.quit()

    @qasync.asyncSlot()
    async def _restart(self):
        await self.start()

    # Create a BaramFlow project by generating a CoreDB.
    # path: None for project creation, or an exported BaramMesh project path for conversion.
    def _createProject(self, path=None):
        app.plug.createProject(self._projectSelector, path)

    # A BaramFlow project or an exported BaramMesh project directory is selected.
    @qasync.asyncSlot()
    async def _projectSelected(self, directory):
        path = Path(directory)
        if not FileDB.exists(path) and isBaramProject(path):
            # Start Case Wizard if a project exported from baramMesh
            self._createProject(path)
        else:
            await self._openProject(path, ProjectOpenType.EXISTING)

    @qasync.asyncSlot()
    async def _openProject(self, path, openType):
        openedProject = None

        try:
            openedProject = await Project.open(path.resolve(), openType)

            batchCases = openedProject.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
            if (batchCases is not None and not batchCases.empty
                    and platform.system() == 'Windows' and not ctypes.windll.shell32.IsUserAnAdmin()):
                # Symbolic link requires administrator permission on Windows platform
                openedProject = None
                await AsyncMessageBox().warning(
                    self._projectSelector, self.tr('Permission Error'),
                    self.tr('Run BARAM as administrator to use batch mode'))
        except FileNotFoundError:
            await AsyncMessageBox().warning(self._projectSelector, self.tr('Project Open Error'),
                                            self.tr(f'{path.name} is not a baram project.'))
        except Timeout:
            await AsyncMessageBox().warning(self._projectSelector, self.tr('Project Open Error'),
                                            self.tr(f'{path.name} is open in another program.'))
        except Exception as ex:
            await AsyncMessageBox().warning(self._projectSelector, self.tr('Project Open Error'),
                                            self.tr('Fail to open case\n' + str(ex)))

        if openedProject is None:
            await Project.close()
            return

        if self._projectSelector is not None:
            self._projectSelector.accept()  # To close project selector dialog
        app.openMainWindow()


