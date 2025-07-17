#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import webbrowser

import qasync
from filelock import Timeout
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QVBoxLayout
from PySide6.QtCore import Signal, QEvent, QMargins
from PySide6QtAds import CDockManager, DockWidgetArea

from libbaram.validation import ValidationError
from libbaram.utils import getFit
from widgets.async_message_box import AsyncMessageBox
from widgets.new_project_dialog import NewProjectDialog
from widgets.parallel.parallel_environment_dialog import ParallelEnvironmentDialog
from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.openfoam.redistribution_task import RedistributionTask
from baramMesh.view.display_control.display_control import DisplayControl
from baramMesh.view.widgets.project_dialog import ProjectDialog
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
    _closeTriggered = Signal(bool)

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

        self._dockManager = CDockManager(self._ui.dockContainer)

        self._navigationView = NavigationView(self._ui.stepButtons)
        self._displayControl = DisplayControl(self._ui)
        self._renderingTool = RenderingTool(self._ui)
        self._consoleView = ConsoleView()

        self._geometryManager: Optional[GeometryManager] = None
        self._meshManager = None
        self._stepManager = StepManager(self._navigationView, self._ui)

        self._startDialog = ProjectDialog()
        self._dialog = None

        self._readyToQuit = False

        self.setWindowIcon(app.properties.icon())

        self._contentLayout = QVBoxLayout(self._ui.content)
        self._contentLayout.setContentsMargins(0, 0, 0, 0)

        self._setupShortcuts()

        self._connectSignalsSlots()

        layout = QVBoxLayout(self._ui.dockContainer)
        layout.setContentsMargins(QMargins(0, 0, 0, 0))
        layout.addWidget(self._dockManager)

        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, self._consoleView)
        
        self._ui.regionValidationMessage.hide()

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
        return self._consoleView.widget()

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
        if not self._readyToQuit:
            self._closeTriggered.emit(True)
            event.ignore()
            return

        app.settings.updateLastMainWindowGeometry(self.geometry())

        self._dockManager.deleteLater()

        super().closeEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self._ui.retranslateUi(self)
            self._stepManager.retranslatePages()

        super().changeEvent(event)

    async def start(self):
        self._startDialog.setRecents(app.settings.getRecentProjects())
        self._startDialog.open()

    def _setupShortcuts(self):
        self._ui.actionNew.setShortcut('Ctrl+N')
        self._ui.actionOpen.setShortcut('Ctrl+O')
        self._ui.actionSave.setShortcut('Ctrl+S')
        self._ui.actionExit.setShortcut('Ctrl+Q')
        self._ui.actionParallelEnvironment.setShortcut('Ctrl+P')
        self._ui.actionLanguage.setShortcut('Ctrl+L')

    def _connectSignalsSlots(self):
        app.renderingToggled.connect(self._setRenderingEnabled)

        self._ui.menuView.addAction(self._consoleView.toggleViewAction())

        self._ui.actionNew.triggered.connect(self._actionNew)
        self._ui.actionOpen.triggered.connect(self._actionOpen)
        self._ui.actionSave.triggered.connect(self._actionSave)
        self._ui.actionSaveAs.triggered.connect(self._actionSaveAs)
        self._ui.actionExit.triggered.connect(self.close)
        self._ui.actionParameters.triggered.connect(self._actionParameters)
        self._ui.actionParallelEnvironment.triggered.connect(self._openParallelEnvironmentDialog)
        self._ui.actionScale.triggered.connect(self._actionScale)
        self._ui.actionLanguage.triggered.connect(self._actionLanguage)
        self._ui.actionAbout.triggered.connect(self._actionAbout)
        self._ui.actionTutorials.triggered.connect(self._openTutorials)

        self._recentFilesMenu.projectSelected.connect(self._openRecent)

        self._startDialog.actionNewSelected.connect(self._actionNew)
        self._startDialog.actionOpenSelected.connect(self._actionOpen)
        self._startDialog.actionProjectSelected.connect(self._openProject)
        self._startDialog.finished.connect(self._startDialogClosed)

        self._stepManager.openedStepChanged.connect(self._displayControl.openedStepChanged)
        self._stepManager.currentStepChanged.connect(self._displayControl.currentStepChanged)

        self._closeTriggered.connect(self._closeProject)

    def _setRenderingEnabled(self, enabled):
        self._displayControl.setEnabled(enabled)
        if enabled:
            self._renderingTool.enable()
            self._geometryManager.show()
            self._stepManager.currentPage().updateMesh()    # This call meshManger.load()
        else:
            self._renderingTool.disable()
            self._geometryManager.hide()
            self._meshManager.unload()

    def _openRecent(self, path):
        self._openProject(path)

    def _actionNew(self):
        self._dialog = NewProjectDialog(self, self.tr('New Project'), Path(app.settings.getRecentLocation()).resolve())
        self._dialog.accepted.connect(self._createProject)
        self._dialog.show()

    def _actionOpen(self):
        self._dialog = QFileDialog(self, self.tr('Select Project Directory'), app.settings.getRecentLocation())
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self._openProject)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _actionSave(self):
        if await self._stepManager.saveCurrentPage():
            app.project.save()

    @qasync.asyncSlot()
    async def _actionSaveAs(self):
        self._dialog = QFileDialog(self, self.tr('Select Project Directory'), app.settings.getRecentLocation())
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self._dialog.fileSelected.connect(self._saveAs)
        # On Windows, finishing a dialog opened with the open method does not redraw the menu bar. Force repaint.
        self._dialog.finished.connect(self._ui.menubar.repaint)
        self._dialog.open()

    def _actionParameters(self):
        self._dialog = MeshQualityParametersDialog(self)
        self._dialog.open()

    def _openParallelEnvironmentDialog(self):
        self._dialog = ParallelEnvironmentDialog(self, app.project.parallelEnvironment())
        if app.fileSystem.timePathExists(1, app.project.parallelCores() > 1):
            self._dialog.setReadOnly()
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

    def _openTutorials(self):
        webbrowser.open('https://baramcfd.org/en/tutorial/baram-mesh/tutorial-mesh-dashboard-en/')

    @qasync.asyncSlot()
    async def _createProject(self):
        await self._closeProject()
        self._clear()

        if app.createProject(self._dialog.projectLocation()):
            self._recentFilesMenu.addRecentest(app.project.path)
            self._projectOpened()

    @qasync.asyncSlot()
    async def _openProject(self, file):
        await self._closeProject()
        self._clear()

        path = Path(file)
        try:
            app.openProject(path.resolve())
            self._projectOpened()
        except FileNotFoundError:
            await AsyncMessageBox().information(self, self.tr('Project Open Error'),
                                                self.tr(f'{path.name} is not a baram project.'))
        except Timeout:
            await AsyncMessageBox().information(self, self.tr('Project Open Error'),
                                    self.tr(f'{path.name} is already open in another program.'))
        except ValidationError as e:
            await AsyncMessageBox().information(self, self.tr('Project Open Error'),
                                                self.tr(f'configurations error : {e.path} - {e.name}'))

    @qasync.asyncSlot()
    async def _saveAs(self, file):
        path = Path(file).resolve()

        if path.exists():
            if not path.is_dir():
                await AsyncMessageBox().information(self, self.tr('Project Directory Error'),
                                                    self.tr(f'{file} is not a directory.'))
                return
            elif os.listdir(path):
                await AsyncMessageBox().information(self, self.tr('Project Directory Error'),
                                                    self.tr(f'{file} is not empty.'))
                return

        if await self._stepManager.saveCurrentPage():
            progressDialog = ProgressDialog(self, self.tr('Save As'))
            progressDialog.open()

            progressDialog.setLabelText(self.tr('Saving Project'))

            app.project.saveAs(path)
            await asyncio.to_thread(app.fileSystem.saveAs, path)
            await self._closeProject()
            self._clear()
            self._projectClosed()
            app.openProject(path)
            self._projectOpened()
            progressDialog.close()

    def _startDialogClosed(self):
        if app.project is None:
            self.close()

        self._ui.menubar.repaint()

    @qasync.asyncSlot()
    async def _closeProject(self, toQuit=False):
        if app.project is None:
            return True

        if not await self._stepManager.saveCurrentPage():
            return False

        if app.db.isModified():
            confirm = await AsyncMessageBox().question(self, self.tr('Save Changed'),
                                                       self.tr('Do you want to save your changes?'),
                                                       QMessageBox.StandardButton.Ok
                                                       | QMessageBox.StandardButton.Cancel
                                                       | QMessageBox.StandardButton.Discard)

            if confirm == QMessageBox.StandardButton.Ok:
                app.project.save()
            elif confirm == QMessageBox.StandardButton.Cancel:
                return False

        app.closeProject()
        self._projectClosed()

        if toQuit:
            self._readyToQuit = True
            self.close()

        return True

    @qasync.asyncSlot()
    async def _updateParallelEnvironment(self):
        environment = self._dialog.environment()
        numCores = environment.np()
        oldNumCores = app.project.parallelCores()

        progressDialog = ProgressDialog(self._dialog, self.tr('Case Redistribution'))
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
        self._recentFilesMenu.updateRecentest(app.project.path)

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

    def _projectClosed(self):
        logging.getLogger().removeHandler(self._handler)
        self._handler.close()

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
