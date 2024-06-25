#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler
import os
import subprocess
from enum import Enum, auto
from pathlib import Path
import platform

import qasync
import asyncio

from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QEvent, QTimer, Signal

from libbaram.run import hasUtility
from libbaram.utils import getFit
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.parallel.parallel_environment_dialog import ParallelEnvironmentDialog

from baramFlow.app import app
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.app_settings import AppSettings
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.project import Project
from baramFlow.mesh.mesh_manager import MeshManager, MeshType
from baramFlow.openfoam import parallel
from baramFlow.openfoam.constant.region_properties import RegionProperties
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.polymesh.polymesh_loader import PolyMeshLoader
from baramFlow.openfoam.redistribution_task import RedistributionTask
from baramFlow.solver_status import SolverStatus
from baramFlow.view.main_window.menu.mesh.poly_meshes_dialog import PolyMeshesDialog
from baramFlow.view.main_window.menu.settrings.settings_language_dialog import SettingLanguageDialog
from baramFlow.view.main_window.menu.settrings.settings_paraveiw_dialog import SettingsParaViewDialog
from baramFlow.view.main_window.menu.settrings.settings_scaling_dialog import SettingScalingDialog
from baramFlow.view.setup.general.general_page import GeneralPage
from baramFlow.view.setup.materials.material_page import MaterialPage
from baramFlow.view.setup.models.models_page import ModelsPage
from baramFlow.view.setup.cell_zone_conditions.cell_zone_conditions_page import CellZoneConditionsPage
from baramFlow.view.setup.boundary_conditions.boundary_conditions_page import BoundaryConditionsPage
from baramFlow.view.setup.reference_values.reference_values_page import ReferenceValuesPage
from baramFlow.view.solution.numerical_conditions.numerical_conditions_page import NumericalConditionsPage
from baramFlow.view.solution.monitors.monitors_page import MonitorsPage
from baramFlow.view.solution.initialization.initialization_page import InitializationPage
from baramFlow.view.solution.run_conditions.run_conditions_page import RunConditionsPage
from baramFlow.view.solution.run.process_information_page import ProcessInformationPage
from .content_view import ContentView
from .dock_view import DockView
from .main_window_ui import Ui_MainWindow
from .menu.mesh.mesh_info_dialog import MeshInfoDialog
from .navigator_view import NavigatorView, MenuItem
from .menu.mesh.mesh_scale_dialog import MeshScaleDialog
from .menu.mesh.mesh_translate_dialog import MeshTranslateDialog
from .menu.mesh.mesh_rotate_dialog import MeshRotateDialog
from .menu.help.about_dialog import AboutDialog

logger = logging.getLogger(__name__)

CCM_TO_FOAM_URL = 'https://openfoamwiki.net/index.php/Ccm26ToFoam'


class CloseType(Enum):
    EXIT_APP = 0
    CLOSE_PROJECT = auto()


class MenuPage:
    def __init__(self, pageClass=None):
        self._pageClass = pageClass
        self._widget = None

    @property
    def widget(self):
        return self._widget

    def createPage(self, parent):
        self._widget = self._pageClass(parent)
        return self._widget

    def removePage(self):
        self._widget = None

    def isCreated(self):
        return self._widget or not self._pageClass


class MainWindow(QMainWindow):
    _closeTriggered = Signal(CloseType)

    def __init__(self):
        super().__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self.setWindowIcon(app.properties.icon())

        self._project = Project.instance()
        self._caseManager = CaseManager()
        # self._caseManager.load()

        # 10MB(=10,485,760=1024*1024*10)
        self._handler = RotatingFileHandler(self._project.path/'log.txt', maxBytes=10485760, backupCount=5)
        self._handler.setFormatter(logging.Formatter("[%(asctime)s][%(name)s] ==> %(message)s"))
        logging.getLogger().addHandler(self._handler)

        self._navigatorView = NavigatorView(self._ui.navigatorView)
        self._contentView = ContentView(self._ui.formView, self._ui)
        self._dockView = DockView(self._ui.menuView)

        self._menuPages = {
            MenuItem.MENU_SETUP.value: MenuPage(),
            MenuItem.MENU_SOLUTION.value: MenuPage(),
            MenuItem.MENU_SETUP_GENERAL.value: MenuPage(GeneralPage),
            MenuItem.MENU_SETUP_MATERIALS.value: MenuPage(MaterialPage),
            MenuItem.MENU_SETUP_MODELS.value: MenuPage(ModelsPage),
            MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value: MenuPage(CellZoneConditionsPage),
            MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value: MenuPage(BoundaryConditionsPage),
            MenuItem.MENU_SETUP_REFERENCE_VALUES.value: MenuPage(ReferenceValuesPage),
            MenuItem.MENU_SOLUTION_NUMERICAL_CONDITIONS.value: MenuPage(NumericalConditionsPage),
            MenuItem.MENU_SOLUTION_MONITORS.value: MenuPage(MonitorsPage),
            MenuItem.MENU_SOLUTION_INITIALIZATION.value: MenuPage(InitializationPage),
            MenuItem.MENU_SOLUTION_RUN_CONDITIONS.value: MenuPage(RunConditionsPage),
            MenuItem.MENU_SOLUTION_RUN.value: MenuPage(ProcessInformationPage),
        }

        self._dialog = None

        self._closeType = None

        self._setupShortcuts()

        self._connectSignalsSlots()

        geometry = AppSettings.getLastMainWindowGeometry()
        display = app.qApplication.primaryScreen().availableVirtualGeometry()
        fit = getFit(geometry, display)
        self.setGeometry(fit)

        self._ui.splitter.addWidget(self._dockView)
        self._ui.splitter.setStretchFactor(2, 1)

    @property
    def dockView(self):
        return self._dockView

    def renderingView(self):
        return self._dockView.renderingView()

    def case(self):
        return self._caseManager

    def load(self):
        self._project.opened()

    def closeEvent(self, event):
        if self._closeType is None:
            self._closeTriggered.emit(CloseType.EXIT_APP)
            event.ignore()
            return

        self._caseManager.clear()
        Project.close()

        if self._closeType == CloseType.CLOSE_PROJECT:
            app.restart()
        else:
            app.quit()

        super().closeEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self._ui.retranslateUi(self)
            self._navigatorView.translate()

            for page in self._menuPages.values():
                if page.isCreated():
                    self._contentView.removePage(page)
                    page.removePage()

            self._loadForm(self._navigatorView.currentMenu())

        super().changeEvent(event)

    def _setupShortcuts(self):
        self._ui.actionSave.setShortcut('Ctrl+S')
        self._ui.actionSaveAs.setShortcut('Ctrl+A')
        self._ui.actionCloseProject.setShortcut('Ctrl+E')
        self._ui.actionExit.setShortcut('Ctrl+Q')

        self._ui.actionParallelEnvironment.setShortcut('Ctrl+P')

        self._ui.actionLanguage.setShortcut('Ctrl+L')

        self._ui.actionParaView.setShortcut('Ctrl+V')

    def _connectSignalsSlots(self):
        self._ui.actionSave.triggered.connect(self._save)
        self._ui.actionSaveAs.triggered.connect(self._saveAs)
        self._ui.actionOpenFoam.triggered.connect(self._importOpenFOAMMesh)
        self._ui.actionMultiplePolyMesh.triggered.connect(self._importMultiplePolyMesh)
        self._ui.actionFluent.triggered.connect(self._importFluentMesh)
        self._ui.actionStarCCM.triggered.connect(self._importStarCcmPlus)
        self._ui.actionGmsh.triggered.connect(self._importGmsh)
        self._ui.actionIdeas.triggered.connect(self._importIdeas)
        self._ui.actionNasaPlot3d.triggered.connect(self._importNasaPlot3D)
        self._ui.actionCloseProject.triggered.connect(lambda: self._closeProject(CloseType.CLOSE_PROJECT))
        self._ui.actionExit.triggered.connect(lambda: self._closeProject(CloseType.EXIT_APP))

        self._ui.actionMeshInfo.triggered.connect(self._openMeshInfoDialog)
        self._ui.actionMeshScale.triggered.connect(self._openMeshScaleDialog)
        self._ui.actionMeshTranslate.triggered.connect(self._openMeshTranslateDialog)
        self._ui.actionMeshRotate.triggered.connect(self._openMeshRotateDialog)

        self._ui.actionParallelEnvironment.triggered.connect(self._openParallelEnvironmentDialog)

        self._ui.actionScale.triggered.connect(self._changeScale)
        self._ui.actionLanguage.triggered.connect(self._changeLanguage)
        self._ui.actionParaViewSetting.triggered.connect(self._openParaViewSettingDialog)

        self._ui.actionParaView.triggered.connect(self._paraViewActionTriggered)

        self._ui.actionAbout.triggered.connect(self._showAboutDialog)

        self._navigatorView.currentMenuChanged.connect(self._changeForm)

        self._project.projectOpened.connect(self._projectOpened)
        self._project.solverStatusChanged.connect(self._solverStatusChanged)

        self._caseManager.caseLoaded.connect(self._caseLoaded)

        self._closeTriggered.connect(self._closeProject)

    @qasync.asyncSlot()
    async def _save(self):
        if await self._saveCurrentPage():
            self._project.save()

    def _saveAs(self):
        QMessageBox.information(self, self.tr('Save as a new project'),
                                self.tr('Only configuration and mesh are saved. (Calculation results are not copied)'))

        self._dialog = QFileDialog(self, self.tr('Select Project Directory'), AppSettings.getRecentLocation())
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self._dialog.finished.connect(self._projectDirectorySelected)
        self._dialog.open()

    async def _saveCurrentPage(self):
        currentPage = self._contentView.currentPage()
        if currentPage:
            return await currentPage.save()

        return True

    def _importOpenFOAMMesh(self):
        self._dialog = QFileDialog(self, self.tr('Select Mesh Directory'), AppSettings.getRecentMeshDirectory())
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self._openFOAMMeshSelected)
        # On Windows, finishing a dialog opened with the open method does not redraw the menu bar. Force repaint.
        self._dialog.finished.connect(self._ui.menubar.repaint)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _importMultiplePolyMesh(self):
        if not await self._checkMultiRegionAvailability():
            return

        self._dialog = PolyMeshesDialog(self)
        self._dialog.accepted.connect(self._polyMeshesSelected)
        # On Windows, finishing a dialog opened with the open method does not redraw the menu bar. Force repaint.
        self._dialog.finished.connect(self._ui.menubar.repaint)
        self._dialog.open()

    def _importFluentMesh(self):
        self._openMeshSelectionDialog(MeshType.FLUENT, self.tr('Fluent (*.cas *.msh)'))

    def _importStarCcmPlus(self):
        if hasUtility(MeshManager.convertUtility(MeshType.STAR_CCM)):
            self._openMeshSelectionDialog(MeshType.STAR_CCM, self.tr('StarCCM+ (*.ccm)'))
        else:
            QMessageBox.information(
                self, self.tr('Mesh Convert'),
                self.tr(f'Converter not found.<br>'
                        f'Install <a href="{CCM_TO_FOAM_URL}">ccmToFoam</a> to convert StarCCM+ Mesh.'
                        f'(Linux only)</a>'))

    def _importGmsh(self):
        self._openMeshSelectionDialog(MeshType.GMSH, self.tr('Gmsh (*.msh)'))

    def _importIdeas(self):
        self._openMeshSelectionDialog(MeshType.IDEAS, self.tr('Ideas (*.unv)'))

    def _importNasaPlot3D(self):
        self._openMeshSelectionDialog(MeshType.NAMS_PLOT3D, self.tr('Plot3d (*.unv)'))

    @qasync.asyncSlot()
    async def _closeProject(self, closeType):
        if not await self._saveCurrentPage():
            return

        if self._project.isModified:
            confirm = await AsyncMessageBox().question(self, self.tr('Save Changed'),
                                                       self.tr('Do you want to save your changes?'),
                                                       QMessageBox.StandardButton.Ok
                                                       | QMessageBox.StandardButton.Cancel
                                                       | QMessageBox.StandardButton.Discard)
            if confirm == QMessageBox.StandardButton.Ok:
                await self._save()
            elif confirm == QMessageBox.StandardButton.Cancel:
                return

        self._dockView.close()
        logging.getLogger().removeHandler(self._handler)
        self._handler.close()

        AppSettings.updateLastMainWindowGeometry(self.geometry())

        self._closeType = closeType
        self.close()

    def _openMeshInfoDialog(self):
        self._dialog = MeshInfoDialog(self)
        self._dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._dialog.show()  # Call "show()" for "ApplicationModal"

    def _openMeshScaleDialog(self):
        self._dialog = MeshScaleDialog(self)
        self._dialog.accepted.connect(self._scaleMesh)
        self._dialog.open()

    def _openMeshTranslateDialog(self):
        self._dialog = MeshTranslateDialog(self)
        self._dialog.accepted.connect(self._translateMesh)
        self._dialog.open()

    def _openMeshRotateDialog(self):
        self._dialog = MeshRotateDialog(self)
        self._dialog.accepted.connect(self._rotateMesh)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _openParallelEnvironmentDialog(self):
        self._dialog = ParallelEnvironmentDialog(self, parallel.getEnvironment())
        self._dialog.accepted.connect(self._updateParallelEnvironment)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _scaleMesh(self):
        if not await self._confirmToReplaceMesh():
            return

        try:
            self._caseManager.deleteCalculationResults()
        except PermissionError:
            await AsyncMessageBox().information(self, self.tr('Permission Denied'),
                                                self.tr('The project directory is open by another program.'))
            return

        progressDialog = ProgressDialog(self, self.tr('Mesh Scaling'))
        progressDialog.open()

        try:
            progressDialog.setLabelText(self.tr('Scaling the mesh.'))
            if await MeshManager().scale(*self._dialog.data()):
                progressDialog.finish(self.tr('Mesh scaling failed.'))
                return

            # Workaround to give some time for QT to set up timer or event loop.
            # This workaround is not necessary on Windows because BARAM for Windows
            #     uses custom-built VTK that is compiled with VTK_ALLOWTHREADS
            await asyncio.sleep(0.1)

            loader = PolyMeshLoader()
            loader.progress.connect(progressDialog.setLabelText)
            await loader.loadVtk()

            progressDialog.finish(self.tr('Mesh scaling is complete'))
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    @qasync.asyncSlot()
    async def _translateMesh(self):
        if not await self._confirmToReplaceMesh():
            return

        try:
            self._caseManager.deleteCalculationResults()
        except PermissionError:
            await AsyncMessageBox().information(self, self.tr('Permission Denied'),
                                                self.tr('The project directory is open by another program.'))
            return

        progressDialog = ProgressDialog(self, self.tr('Mesh Translation'))
        progressDialog.open()

        try:
            progressDialog.setLabelText(self.tr('Translating the mesh.'))
            if await MeshManager().translate(*self._dialog.data()):
                progressDialog.finish(self.tr('Mesh translation failed.'))
                return

            # Workaround to give some time for QT to set up timer or event loop.
            # This workaround is not necessary on Windows because BARAM for Windows
            #     uses custom-built VTK that is compiled with VTK_ALLOWTHREADS
            await asyncio.sleep(0.1)

            loader = PolyMeshLoader()
            loader.progress.connect(progressDialog.setLabelText)
            await loader.loadVtk()

            progressDialog.finish(self.tr('Mesh translation is complete'))
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    @qasync.asyncSlot()
    async def _rotateMesh(self):
        if not await self._confirmToReplaceMesh():
            return

        try:
            self._caseManager.deleteCalculationResults()
        except PermissionError:
            await AsyncMessageBox().information(self, self.tr('Permission Denied'),
                                                self.tr('The project directory is open by another program.'))
            return

        progressDialog = ProgressDialog(self, self.tr('Mesh Rotation'))
        progressDialog.open()

        try:
            progressDialog.setLabelText(self.tr('Rotating the mesh.'))
            if await MeshManager().rotate(*self._dialog.data()):
                progressDialog.finish(self.tr('Mesh rotation failed.'))
                return

            # Workaround to give some time for QT to set up timer or event loop.
            # This workaround is not necessary on Windows because BARAM for Windows
            #     uses custom-built VTK that is compiled with VTK_ALLOWTHREADS
            await asyncio.sleep(0.1)

            loader = PolyMeshLoader()
            loader.progress.connect(progressDialog.setLabelText)
            await loader.loadVtk()

            progressDialog.finish(self.tr('Mesh rotation is complete'))
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    @qasync.asyncSlot()
    async def _updateParallelEnvironment(self):
        environment = self._dialog.environment()
        numCores = environment.np()
        oldNumCores = parallel.getNP()

        parallel.setEnvironment(environment)

        progressDialog = ProgressDialog(self, self.tr('Case Redistribution'))
        progressDialog.open()

        if numCores != oldNumCores:
            progressDialog.setLabelText('Redistributing Case')

            try:
                redistributionTask = RedistributionTask()
                redistributionTask.progress.connect(progressDialog.setLabelText)

                await redistributionTask.redistribute()

            except RuntimeError as e:
                progressDialog.finish(str(e))

        progressDialog.finish('Parallel Environment was Applied.')

    async def _loadVtkMesh(self):
        progressDialog = ProgressDialog(self, self.tr('Case Loading.'))
        progressDialog.open()

        # Workaround to give some time for QT to set up timer or event loop.
        # This workaround is not necessary on Windows because BARAM for Windows
        #     uses custom-built VTK that is compiled with VTK_ALLOWTHREADS
        await asyncio.sleep(0.1)

        loader = PolyMeshLoader()
        loader.progress.connect(progressDialog.setLabelText)
        await loader.loadVtk()

        progressDialog.close()

    @qasync.asyncSlot()
    async def _changeForm(self, currentMenu, previousMenu=-1):
        if previousMenu > -1:
            previousPage = self._menuPages[previousMenu]
            if previousPage.widget and previousPage.widget == self._contentView.currentPage():
                if not await previousPage.widget.save() or not previousPage.widget.checkToQuit():
                    QTimer.singleShot(0, lambda: self._navigatorView.setCurrentMenu(previousMenu))
                    return

        self._loadForm(currentMenu)

    def _loadForm(self, currentMenu):
        page = self._menuPages[currentMenu]
        if not page.isCreated():
            page.createPage(self._ui.formView)
            self._contentView.addPage(page)

        self._contentView.changePane(page)

    def _showAboutDialog(self):
        self._dialog = AboutDialog(self)
        self._dialog.open()

    def meshUpdated(self):
        if RegionDB.getNumberOfRegions() > 1:  # multi-region
            ModelsDB.EnergyModelOn()

        self._project.save()
        # self._ui.menuMesh.setEnabled(True)
        # self._ui.menuParallel.setEnabled(True)
        self._navigatorView.updateEnabled()

        targets = [
            MenuItem.MENU_SETUP_MODELS.value,
            MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value,
            MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value,
            MenuItem.MENU_SOLUTION_NUMERICAL_CONDITIONS.value,
            MenuItem.MENU_SOLUTION_MONITORS.value,
            MenuItem.MENU_SOLUTION_INITIALIZATION.value,
        ]

        for page in [self._menuPages[menu] for menu in targets]:
            if page.isCreated():
                self._contentView.removePage(page)
                page.removePage()

        currentMenu = self._navigatorView.currentMenu()
        if currentMenu in targets:
            self._loadForm(currentMenu)

    @qasync.asyncSlot()
    async def _solverStatusChanged(self, status, liveStatusChanged=False):
        batchRunning = CaseManager().isBatchRunning()
        solverRunning = status == SolverStatus.RUNNING or batchRunning

        self._ui.actionSaveAs.setDisabled(solverRunning)
        self._ui.menuLoadMesh.setDisabled(solverRunning)
        self._ui.menuMesh.setDisabled(solverRunning)
        self._ui.menuParallel.setDisabled(solverRunning)
        self._ui.actionCloseProject.setDisabled(batchRunning)

        self._navigatorView.updateEnabled()

        if status == SolverStatus.ENDED and liveStatusChanged:
            await AsyncMessageBox().information(self, self.tr('Calculation Terminated'),
                                                self.tr('Calculation is terminated.'))

    @qasync.asyncSlot()
    async def _projectOpened(self):
        self._caseManager.load()

        if self._caseManager.isRunning():
            self._navigatorView.setCurrentMenu(MenuItem.MENU_SOLUTION_RUN.value)
            self._dockView.showChartDock()
        else:
            self._navigatorView.setCurrentMenu(MenuItem.MENU_SETUP_GENERAL.value)
            self._dockView.showRenderingDock()

        db = coredb.CoreDB()
        if db.hasMesh():
            await self._loadVtkMesh()
        elif FileSystem.hasPolyMesh():
            # BaramMesh Project is opened
            progressDialog = ProgressDialog(self, self.tr('Mesh Loading'))
            progressDialog.open()

            # Workaround to give some time for QT to set up timer or event loop.
            # This workaround is not necessary on Windows because BARAM for Windows
            #     uses custom-built VTK that is compiled with VTK_ALLOWTHREADS
            await asyncio.sleep(0.1)

            try:
                loader = PolyMeshLoader()
                loader.progress.connect(progressDialog.setLabelText)
                await loader.loadMesh()

                progressDialog.close()
            except Exception as ex:
                progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

            self._project.fileDB().saveCoreDB()

        self._navigatorView.updateEnabled()

    @qasync.asyncSlot()
    async def _caseLoaded(self, name=None):
        if name:
            self.setWindowTitle(f'{app.properties.fullName} - {name} ({self._project.path})')
        else:
            self.setWindowTitle(f'{app.properties.fullName} - {self._project.path}')

    def _changeScale(self):
        self._dialog = SettingScalingDialog(self)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _changeLanguage(self):
        await self._saveCurrentPage()
        self._dialog = SettingLanguageDialog(self)
        self._dialog.open()

    def _openParaViewSettingDialog(self):
        self._dialog = SettingsParaViewDialog(self)
        self._dialog.open()

    def _paraViewActionTriggered(self):
        if path := AppSettings.findParaviewInstalledPath():
            self._runParaView(path, False)
            return

        if platform.system() == 'Windows':
            self._dialog = QFileDialog(self, self.tr('Select ParaView Executable'), os.environ.get('PROGRAMFILES'), 'exe (*.exe)')
        else:
            self._dialog = QFileDialog(self, self.tr('Select ParaView Executable'))
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._dialog.fileSelected.connect(self._runParaView)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _projectDirectorySelected(self, result):
        # On Windows, finishing a dialog opened with the open method does not redraw the menu bar. Force repaint.
        self._ui.menubar.repaint()

        if dirs := self._dialog.selectedFiles():
            path = Path(dirs[0]).resolve()

            if path.exists():
                if not path.is_dir():
                    QMessageBox.critical(self, self.tr('Case Directory Error'),
                                         self.tr(f'{dirs[0]} is not a directory.'))
                    return
                elif os.listdir(path):
                    QMessageBox.critical(self, self.tr('Case Directory Error'), self.tr(f'{dirs[0]} is not empty.'))
                    return

            if await self._saveCurrentPage():
                progressDialog = ProgressDialog(self, self.tr('Save As'))
                progressDialog.open()

                progressDialog.setLabelText(self.tr('Saving case'))

                await asyncio.to_thread(FileSystem.saveAs, self._project.path, path, coredb.CoreDB().getRegions())
                self._project.saveAs(path)
                progressDialog.close()

    def _openMeshSelectionDialog(self, meshType, fileFilter=None):
        self._dialog = QFileDialog(self, self.tr('Select Mesh Directory'),
                                   AppSettings.getRecentMeshDirectory(), fileFilter)
        self._dialog.fileSelected.connect(lambda file: self._meshFileSelected(file, meshType))
        # On Windows, finishing a dialog opened with the open method does not redraw the menu bar. Force repaint.
        self._dialog.finished.connect(self._ui.menubar.repaint)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _openFOAMMeshSelected(self, directory):
        AppSettings.updateRecentMeshDirectory(str(directory))

        path = Path(directory)
        if len(RegionProperties.loadRegions(path)) > 1 and not await self._checkMultiRegionAvailability():
            return

        if not await self._confirmAndClearMeshFiles():
            return

        meshManager = MeshManager()
        progressDialog = ProgressDialog(self, self.tr('Mesh Importing'))

        try:
            progressDialog.open()

            progressDialog.setLabelText(self.tr('Copying files.'))
            await meshManager.importMeshFiles(path)

            progressDialog.close()

            await self._loadMesh()
        except Exception as ex:
            self._deleteMeshFilesAndData()
            progressDialog.finish(self.tr('Mesh import failed:\n' + str(ex)))

    @qasync.asyncSlot()
    async def _polyMeshesSelected(self):
        if not await self._confirmAndClearMeshFiles():
            return

        progressDialog = ProgressDialog(self, self.tr('Mesh Importing'))

        try:
            progressDialog.open()

            progressDialog.setLabelText(self.tr('Copying files.'))
            await MeshManager().importPolyMeshes(self._dialog.data())

            progressDialog.close()

            await self._loadMesh()
        except Exception as ex:
            self._deleteMeshFilesAndData()
            progressDialog.finish(self.tr('Mesh import failed:\n' + str(ex)))

    @qasync.asyncSlot()
    async def _meshFileSelected(self, file, meshType):
        AppSettings.updateRecentMeshDirectory(str(file))

        if not await self._confirmAndClearMeshFiles():
            return

        meshManager = MeshManager()
        progressDialog = ProgressDialog(self, self.tr('Mesh Importing'))

        try:
            progressDialog.open()

            progressDialog.setLabelText(self.tr('Converting the mesh.'))
            progressDialog.cancelClicked.connect(meshManager.cancel)
            progressDialog.showCancelButton()
            await meshManager.convertMesh(Path(file), meshType)

            progressDialog.close()

            await self._loadMesh()
        except Exception as ex:
            self._deleteMeshFilesAndData()
            progressDialog.finish(self.tr('Mesh import failed:\n' + str(ex)))

    async def _loadMesh(self):
        progressDialog = ProgressDialog(self, self.tr('Mesh Loading'))
        progressDialog.open()

        # Workaround to give some time for QT to set up timer or event loop.
        # This workaround is not necessary on Windows because BARAM for Windows
        #     uses custom-built VTK that is compiled with VTK_ALLOWTHREADS
        await asyncio.sleep(0.1)

        try:
            loader = PolyMeshLoader()
            loader.progress.connect(progressDialog.setLabelText)
            await loader.loadMesh()

            redistributeTask = RedistributionTask()
            redistributeTask.progress.connect(progressDialog.setLabelText)
            await redistributeTask.redistribute()

            progressDialog.close()
            return
        except Exception as ex:
            progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

    def _runParaView(self, executable, updateSetting=True):
        casePath = FileSystem.foamFilePath()
        subprocess.Popen([executable, str(casePath)])
        if updateSetting:
            AppSettings.updateParaviewInstalledPath(executable)

    async def _confirmToReplaceMesh(self):
        if coredb.CoreDB().getRegions():
            confirm = await AsyncMessageBox().question(
                self, self.tr('Load Mesh'),
                self.tr('This action will overwrite current mesh, related configurations, and calculation data.\n'
                        'It cannot be recovered, and changed configurations will be saved automatically.'))

            if confirm != QMessageBox.StandardButton.Yes:
                return False

        return True

    async def _confirmAndClearMeshFiles(self):
        try:
            if await self._confirmToReplaceMesh():
                self._caseManager.clearCases()

                return True
        except PermissionError:
            await AsyncMessageBox().information(self, self.tr('Permission Denied'),
                                                self.tr('The project directory is open by another program.'))

        return False

    async def _checkMultiRegionAvailability(self):
        if ModelsDB.isMultiphaseModelOn():
            await AsyncMessageBox().information(
                self, self.tr('Invalid mesh'),
                self.tr('Multi-region cases cannot be computed under multi-phase conditions.'))
            return False

        if GeneralDB.isDensityBased():
            await AsyncMessageBox().information(
                self, self.tr('Invalid mesh'),
                self.tr('Multi-region cases cannot be computed under density-based conditions.'))
            return False

        return True

    def _deleteMeshFilesAndData(self):
        db = coredb.CoreDB()
        db.clearRegions()
        db.clearMonitors()
        FileSystem.deleteMesh()
        self.meshUpdated()
