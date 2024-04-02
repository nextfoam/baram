#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import qasync
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from filelock import Timeout
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QVBoxLayout
from PySide6.QtCore import Signal, QEvent

from libbaram.utils import getFit
from widgets.parallel.parallel_environment_dialog import ParallelEnvironmentDialog
from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.openfoam.redistribution_task import RedistributionTask
from baramMesh.view.display_control.display_control import DisplayControl
from baramMesh.view.widgets.project_dialog import ProjectDialog
from baramMesh.view.widgets.new_project_dialog import NewProjectDialog
from baramMesh.view.widgets.settings_scaling_dialog import SettingScalingDialog
from baramMesh.view.widgets.language_dialog import LanugageDialog
from baramMesh.view.menu.mesh_quality.mesh_quality_parameters_dialog import MeshQualityParametersDialog
from baramMesh.view.menu.help.about_dialog import AboutDialog
from baramMesh.view.geometry.geometry_manager import GeometryManager
from .recent_files_menu import RecentFilesMenu
from .naviagtion_view import NavigationView
from .rendering_tool import RenderingTool
from .console_view import ConsoleView
from .mesh_manager import MeshManager
from .step_manager import StepManager
from .main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow):
    _vtkReaderProgress = Signal(str)

    def __init__(self):
        super().__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self._ui.renderingSplitter.setStretchFactor(0, 0)
        self._ui.renderingSplitter.setStretchFactor(1, 1)
        self._ui.centralSplitter.setStretchFactor(0, 0)
        self._ui.centralSplitter.setStretchFactor(1, 1)
        self._ui.centralSplitter.adjustSize()

        self._recentFilesMenu = RecentFilesMenu(self._ui.menuOpen_Recent)
        self._recentFilesMenu.setRecents(app.settings.getRecentProjects())

        self._navigationView = NavigationView(self._ui.stepButtons)
        self._displayControl = DisplayControl(self._ui)
        self._renderingTool = RenderingTool(self._ui)
        self._consoleView = ConsoleView(self._ui)

        self._geometryManager: Optional[GeometryManager] = None
        self._meshManager = None
        self._stepManager = StepManager(self._navigationView, self._ui)

        self._startDialog = ProjectDialog()
        self._dialog = None

        self.setWindowIcon(app.properties.icon())

        self._contentLayout = QVBoxLayout(self._ui.content)
        self._contentLayout.setContentsMargins(0, 0, 0, 0)

        self._connectSignalsSlots()

        geometry = app.settings.getLastMainWindowGeometry()
        display = app.qApplication.primaryScreen().availableVirtualGeometry()
        fit = getFit(geometry, display)
        self.setGeometry(fit)

    @property
    def stepManager(self):
        return self._stepManager

    @property
    def renderingView(self):
        return self._ui.renderingView

    @property
    def consoleView(self):
        return self._consoleView

    @property
    def displayControl(self):
        return self._displayControl

    @property
    def geometryManager(self) -> GeometryManager:
        return self._geometryManager

    @property
    def meshManager(self):
        return self._meshManager

    def closeEvent(self, event):
        if not self._closeProject():
            event.ignore()
            return

        app.settings.updateLastMainWindowGeometry(self.geometry())

        event.accept()

    def changeEvent(self, event):
        if event.type() == QEvent.LanguageChange:
            self._ui.retranslateUi(self)
            self._stepManager.retranslatePages()

        super().changeEvent(event)

    async def start(self):
        self._startDialog.setRecents(app.settings.getRecentProjects())
        self._startDialog.open()

    def _connectSignalsSlots(self):
        self._ui.menuView.addAction(self._ui.consoleView.toggleViewAction())

        self._ui.actionNew.triggered.connect(self._actionNew)
        self._ui.actionOpen.triggered.connect(self._actionOpen)
        self._ui.actionSave.triggered.connect(self._actionSave)
        self._ui.actionExit.triggered.connect(self.close)
        self._ui.actionParameters.triggered.connect(self._actionParameters)
        self._ui.actionParallelEnvironment.triggered.connect(self._openParallelEnvironmentDialog)
        self._ui.actionScale.triggered.connect(self._actionScale)
        self._ui.actionLanguage.triggered.connect(self._actionLanguage)
        self._ui.actionAbout.triggered.connect(self._actionAbout)

        self._recentFilesMenu.projectSelected.connect(self._openRecent)

        self._startDialog.actionNewSelected.connect(self._actionNew)
        self._startDialog.actionOpenSelected.connect(self._actionOpen)
        self._startDialog.actionProjectSelected.connect(self._openProject)
        self._startDialog.finished.connect(self._startDialogClosed)

        self._stepManager.openedStepChanged.connect(self._displayControl.openedStepChanged)
        self._stepManager.currentStepChanged.connect(self._displayControl.currentStepChanged)

    def _openRecent(self, path):
        self._openProject(path)

    def _actionNew(self):
        self._dialog = NewProjectDialog(self)
        self._dialog.setBaseLocation(Path(app.settings.getRecentLocation()).resolve())
        self._dialog.accepted.connect(self._createProject)
        self._dialog.show()

    def _actionOpen(self):
        self._dialog = QFileDialog(self, self.tr('Select Project Directory'), app.settings.getRecentLocation())
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self._openProject)
        self._dialog.open()

    def _actionSave(self):
        if self._stepManager.saveCurrentPage():
            app.project.save()

    def _actionParameters(self):
        self._dialog = MeshQualityParametersDialog(self)
        self._dialog.open()

    def _openParallelEnvironmentDialog(self):
        self._dialog = ParallelEnvironmentDialog(self, app.project.parallelEnvironment())
        self._dialog.accepted.connect(self._updateParallelEnvironment)
        self._dialog.open()

    def _actionScale(self):
        self._dialog = SettingScalingDialog(self, app.settings.getScale())
        self._dialog.accepted.connect(self._changeScale)
        self._dialog.open()

    def _actionLanguage(self):
        self._dialog = LanugageDialog(self)
        self._dialog.open()

    def _actionAbout(self):
        self._dialog = AboutDialog(self)
        self._dialog.open()

    def _createProject(self):
        self._closeProject()
        self._clear()

        if app.createProject(self._dialog.projectLocation()):
            self._recentFilesMenu.addRecentest(app.project.path)
            self._projectOpened()

    def _openProject(self, file):
        self._closeProject()
        self._clear()

        path = Path(file)
        try:
            app.openProject(path.resolve())
            self._recentFilesMenu.updateRecentest(app.project.path)
            self._projectOpened()
        except FileNotFoundError:
            QMessageBox.information(self, self.tr('Case Open Error'), self.tr(f'{path.name} is not a baram case.'))
        except Timeout:
            QMessageBox.information(self, self.tr('Case Open Error'),
                                    self.tr(f'{path.name} is already open in another program.'))

    def _startDialogClosed(self):
        if app.project is None:
            self.close()

    def _closeProject(self):
        if app.project is None:
            return True

        if not self._stepManager.saveCurrentPage():
            return False

        if app.db.isModified():
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.tr('Save Changed'))
            msgBox.setText(self.tr('Do you want save your changes?'))
            msgBox.setStandardButtons(QMessageBox.StandardButton.Ok
                                      | QMessageBox.StandardButton.Discard
                                      | QMessageBox.StandardButton.Cancel)
            msgBox.setDefaultButton(QMessageBox.StandardButton.Ok)

            result = msgBox.exec()
            if result == QMessageBox.StandardButton.Ok:
                app.project.save()
            elif result == QMessageBox.StandardButton.Cancel:
                return False

        app.closeProject()

        logging.getLogger().removeHandler(self._handler)
        self._handler.close()

        return True

    @qasync.asyncSlot()
    async def _updateParallelEnvironment(self):
        environment = self._dialog.environment()
        numCores = environment.np()
        oldNumCores = app.project.parallelCores()

        progressDialog = ProgressDialog(self, self.tr('Case Redistribution'))
        progressDialog.open()

        if numCores != oldNumCores:
            progressDialog.setLabelText('Redistributing Case')

            redistributionTask = RedistributionTask(app.fileSystem)
            redistributionTask.progress.connect(progressDialog.setLabelText)

            await redistributionTask.redistribute(numCores)

        app.project.setParallelEnvironment(environment)
        progressDialog.finish('Parallel Environment was Applied.')

    def _changeScale(self):
        if app.settings.setScale(self._dialog.scale()):
            QMessageBox.information(self, self.tr("Change Scale"), self.tr('Application restart is required.'))

    def _projectOpened(self):
        # 10MB(=10,485,760=1024*1024*10)
        self._handler = RotatingFileHandler(app.project.path / 'log.txt', maxBytes=10485760, backupCount=5)
        self._handler.setFormatter(logging.Formatter("[%(asctime)s][%(name)s] ==> %(message)s"))
        logging.getLogger().addHandler(self._handler)

        if self._startDialog.isVisible():
            self._startDialog.close()
            self.show()

        self.setWindowTitle(f'{app.properties.fullName} - {app.project.path}')

        self._geometryManager = GeometryManager()
        self._meshManager = MeshManager()
        self._meshManager.cellCountChanged.connect(self._cellCountChanged)

        self._geometryManager.load()
        self._stepManager.load()

    def _clear(self):
        self.setWindowTitle(f'{app.properties.fullName}')
        self._renderingTool.clear()
        self._displayControl.clear()
        self._consoleView.clear()
        self._geometryManager = None
        self._meshManager = None

        self._cellCountChanged(0)

    def _cellCountChanged(self, count: int):
        self._ui.cellCount.setText(f'{count:,}')
