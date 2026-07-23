#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import platform
import webbrowser

import qasync
from filelock import Timeout
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QVBoxLayout, QApplication
from PySide6.QtCore import Signal, QEvent, QMargins, Qt
from PySide6QtAds import CDockManager, DockWidgetArea

from analytics import Analytics
from app_properties import meshAppProperties

from libbaram.simple_db.simple_schema import ValidationError
from libbaram.utils import getFit
from widgets.async_message_box import AsyncMessageBox
from widgets.new_project_dialog import NewProjectDialog
from widgets.parallel.parallel_environment_dialog import ParallelEnvironmentDialog
from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.openfoam.redistribution_task import RedistributionTask
from baramMesh.openfoam.utility.snappy_hex_mesh import snappyHexMesh
from baramMesh.view.display_control.display_control import DisplayControl
from baramMesh.view.widgets.project_dialog import ProjectDialog
from baramMesh.view.widgets.settings_scaling_dialog import SettingScalingDialog
from baramMesh.view.widgets.language_dialog import LanugageDialog
from baramMesh.view.menu.mesh_quality.mesh_quality_parameters_dialog import MeshQualityParametersDialog
from baramMesh.view.menu.help.about_dialog import AboutDialog
from baramMesh.view.geometry.geometry_manager import GeometryManager
from widgets.themed_icon import load_themed_icon
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

        self._ui.axis.setIcon(load_themed_icon(':/graphicsIcons/originAxes'))
        self._ui.cubeAxis.setIcon(load_themed_icon(':/graphicsIcons/ruler.svg'))
        self._ui.ruler.setIcon(load_themed_icon(':/graphicsIcons/distance.svg'))
        self._ui.perspective.setIcon(load_themed_icon(':/graphicsIcons/2d-label-icon.svg'))
        self._ui.fit.setIcon(load_themed_icon(':/icons/expand.svg'))
        self._ui.alignAxis.setIcon(load_themed_icon(':/graphicsIcons/alignAxis.svg'))
        self._ui.rotate.setIcon(load_themed_icon(':/icons/reload.svg'))
        self._ui.rotationCenter.setIcon(load_themed_icon(':/graphicsIcons/rotationCenter'))

        self._ui.renderingSplitter.setStretchFactor(0, 0)
        self._ui.renderingSplitter.setStretchFactor(1, 1)
        self._ui.centralSplitter.setStretchFactor(0, 0)
        self._ui.centralSplitter.setStretchFactor(1, 1)
        self._ui.centralSplitter.adjustSize()

        self._recentFilesMenu = RecentFilesMenu(self._ui.menuOpen_Recent)
        self._recentFilesMenu.setRecents(app.settings.getRecentProjects())

        self._dockManager = CDockManager(self._ui.dockContainer)

        self._navigationView = NavigationView(self._ui)
        self._displayControl = DisplayControl(self._ui)
        self._renderingTool = RenderingTool(self._ui)
        self._consoleView = ConsoleView()

        self._geometryManager: Optional[GeometryManager] = None
        self._meshManager = None
        self._stepManager = StepManager(self._navigationView, self._ui)

        self._startDialog = None
        self._setupStartDialog()
        self._dialog = None

        self._readyToQuit = False

        self.setWindowIcon(meshAppProperties.icon())

        # OEM variants with analytics disabled don't need this entry.
        self._ui.actionPrivacySettings.setVisible(Analytics().configured)

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

    def _setupStartDialog(self):
        self._startDialog = ProjectDialog()
        self._startDialog.actionNewSelected.connect(self._actionNew)
        self._startDialog.actionOpenSelected.connect(self._actionOpen)
        self._startDialog.actionProjectSelected.connect(self._openProject)
        self._startDialog.finished.connect(self._startDialogClosed)

    def _returnToStartScreen(self):
        # A project open/create failed after the previous project was already
        # closed, leaving no open project. Hide the now-projectless main window
        # and bring back the start dialog so the user isn't left with a UI that
        # crashes on every action that touches app.db (which is now None).
        self.hide()
        self._setupStartDialog()
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
        self._ui.actionPrivacySettings.triggered.connect(self._openPrivacySettings)

        self._recentFilesMenu.projectSelected.connect(self._openRecent)

        self._stepManager.workingStepChanged.connect(self._displayControl.openedStepChanged)
        self._stepManager.displayStepChanged.connect(self._displayControl.currentStepChanged)

        snappyHexMesh.snappyStarted.connect(self._disableMenubar)
        snappyHexMesh.snappyStopped.connect(self._enableMenubar)

        self._closeTriggered.connect(self._closeProjectSlot)

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
        self._dialog = NewProjectDialog(self, self.tr('New Project'), Path(app.settings.getRecentLocation()).resolve(),
                                        meshAppProperties.projectSuffix)
        self._dialog.accepted.connect(self._createProject)
        self._dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        # QDialog.open() makes the dialog window modal.
        self._dialog.show()

    def _actionOpen(self):
        self._dialog = QFileDialog(self, self.tr('Select Project Directory'), app.settings.getRecentLocation())
        if platform.system() == 'Darwin':  # "show()" for native File dialog does not seem to work on macOS
            self._dialog.setOption(QFileDialog.Option.DontUseNativeDialog)

        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self._openProject)
        self._dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._dialog.show()

    @qasync.asyncSlot()
    async def _actionSave(self):
        if await self._stepManager.saveCurrentPage():
            app.project.save()

    def _actionSaveAs(self):
        self._dialog = NewProjectDialog(self, self.tr('Save as new project'),
                                        Path(app.settings.getRecentLocation()).resolve(), meshAppProperties.projectSuffix)
        self._dialog.pathSelected.connect(self._saveAs)
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
        webbrowser.open('https://baramcfd.org/en/tutorials-en/tutorial-barammesh-en/tutorial-barammesh-en/')

    def _openPrivacySettings(self):
        Analytics().editConsent(parent=self)

    @qasync.asyncSlot()
    async def _createProject(self):
        if not await self._closeProject():  # user cancelled, keep current project
            return
        self._clear()

        try:
            app.createProject(self._dialog.projectPath())
        except (OSError, Timeout) as ex:
            await AsyncMessageBox().information(self, self.tr('Project Creation Error'), str(ex))
            self._recoverFromMissingProject()
            return

        self._recentFilesMenu.addRecentest(app.project.path)
        self._projectOpened()

    @qasync.asyncSlot()
    async def _openProject(self, file):
        if not await self._closeProject():  # user cancelled, keep current project
            return
        self._clear()

        path = Path(file)
        try:
            app.openProject(path.resolve())
            self._projectOpened()
            return
        except FileNotFoundError:
            message = self.tr('{0} is not a {1} project.').format(path.name, meshAppProperties.fullName)
        except Timeout:
            message = self.tr('{0} is already open in another program.').format(path.name)
        except ValidationError as e:
            message = self.tr(f'configurations error : {e.path} - {e.name}')

        await AsyncMessageBox().information(self, self.tr('Project Open Error'), message)
        self._recoverFromMissingProject()

    def _recoverFromMissingProject(self):
        # The open/create failed after the previous project was already closed.
        # If the main window is showing (an in-session switch), it now has no
        # project and every db-backed action would crash, so go back to the
        # start screen. At launch the start dialog is still up, so leave it.
        if self._startDialog is None:
            self._returnToStartScreen()

    @qasync.asyncSlot()
    async def _saveAs(self, path):
        if await self._stepManager.saveCurrentPage():
            progressDialog = ProgressDialog(self, self.tr('Save As'))
            progressDialog.open()

            progressDialog.setLabelText(self.tr('Saving Project'))

            app.project.saveAs(path)
            await asyncio.to_thread(app.fileSystem.saveAs, path)
            await self._closeProject()
            self._clear()
            self._projectClosed()

            try:
                app.openProject(path)
            except (FileNotFoundError, Timeout, ValidationError) as ex:
                # The new project was already written to disk by saveAs above, but
                # reopening it failed after the old project was closed and cleared,
                # leaving the window project-less. Go back to the start screen
                # instead of leaving a UI that crashes on every db-backed action
                # (e.g. meshManager is now None).
                progressDialog.close()
                await AsyncMessageBox().information(self, self.tr('Project Open Error'), str(ex))
                self._recoverFromMissingProject()
                return

            self._projectOpened()
            progressDialog.close()

    def _startDialogClosed(self):
        if app.project is None:
            QApplication.instance().quit()
        else:
            self._ui.menubar.repaint()

    def _disableMenubar(self):
        self._ui.menuFile.setEnabled(False)
        self._ui.menuMesh_Quality.setEnabled(False)
        self._ui.menuParallel.setEnabled(False)

    def _enableMenubar(self):
        self._ui.menuFile.setEnabled(True)
        self._ui.menuMesh_Quality.setEnabled(True)
        self._ui.menuParallel.setEnabled(True)

    @qasync.asyncSlot()
    async def _closeProjectSlot(self, toQuit=False):
        return await self._closeProject(toQuit)

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
        await progressDialog.finish('Parallel Environment was Applied.')

    def _changeScale(self):
        if app.settings.setScale(self._dialog.scale()):
            QMessageBox.information(self, self.tr("Change Scale"), self.tr('Application restart is required.'))

    def _projectOpened(self):
        self._recentFilesMenu.updateRecentest(app.project.path)

        # 10MB(=10,485,760=1024*1024*10)
        self._handler = RotatingFileHandler(app.project.path / 'log.txt', maxBytes=10485760, backupCount=5)
        self._handler.setFormatter(logging.Formatter("[%(asctime)s][%(name)s] ==> %(message)s"))
        logging.getLogger().addHandler(self._handler)

        if self._startDialog is not None:
            self._startDialog.close()
            self.show()
            self._startDialog = None

        self.setWindowTitle(f'{meshAppProperties.fullName} - {app.project.path}')

        self._geometryManager = GeometryManager()
        self._meshManager = MeshManager()
        self._meshManager.cellCountChanged.connect(self._cellCountChanged)

        self._geometryManager.load()
        self._stepManager.load()

    def _projectClosed(self):
        logging.getLogger().removeHandler(self._handler)
        self._handler.close()

    def _clear(self):
        self.setWindowTitle(f'{meshAppProperties.fullName}')
        self._renderingTool.clear()
        self._displayControl.clear()
        self._consoleView.clear()
        self._geometryManager = None
        self._meshManager = None

        self._cellCountChanged(0)

    def _cellCountChanged(self, count: int):
        self._ui.cellCount.setText(f'{count:,}')
