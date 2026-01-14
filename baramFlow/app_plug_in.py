#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtCore import QObject

from baramFlow.app import app
from baramFlow.coredb.project import ProjectOpenType
from baramFlow.view.main_window.main_window import MainWindow
from baramFlow.view.case_wizard.case_wizard import CaseWizard


class AppPlugIn(QObject):
    def __init__(self):
        super().__init__()

        self._caseWizard = None

    def createMainWindow(self):
        """
        Creates a main window.
        Called when project is opened by the project selection dialog.

        """
        return MainWindow()

    def createProject(self, parent, path=None):
        """
        Creates a new project.
        Called when the new button is clicked in the project selection dialog.
        Must create coreDB and emit app.projectCreated signal.

        """
        self._caseWizard = CaseWizard(parent, path)
        self._caseWizard.accepted.connect(self._createCase)
        self._caseWizard.open()

    def _createCase(self):
        path = Path(self._caseWizard.field('projectPath'))
        path.mkdir(exist_ok=True)
        app.projectCreated.emit(path, ProjectOpenType.MESH if self._caseWizard.isMeshProject() else ProjectOpenType.NEW)
