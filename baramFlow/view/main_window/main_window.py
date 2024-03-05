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

from PySide6.QtWidgets import QMainWindow, QWidget, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QEvent, QTimer

from libbaram.run import hasUtility
from libbaram.utils import getFit
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.parallel.parallel_environment_dialog import ParallelEnvironmentDialog

from baramFlow.app import app
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.app_settings import AppSettings
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.project import Project
from baramFlow.mesh.mesh_manager import MeshManager, MeshType
from baramFlow.openfoam import parallel
from baramFlow.openfoam.constant.region_properties import RegionProperties
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.polymesh.polymesh_loader import PolyMeshLoader
from baramFlow.openfoam.redistribution_task import RedistributionTask
from baramFlow.solver_status import SolverStatus
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
from .main_window_ui import Ui_MainWindow
from .menu.mesh.mesh_info_dialog import MeshInfoDialog
from .navigator_view import NavigatorView, MenuItem
from .rendering_dock import RenderingDock
from .console_dock import ConsoleDock
from .chart_dock import ChartDock
from .monitor_dock import MonitorDock
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
    def __init__(self):
        super().__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self.setWindowIcon(app.properties.icon())

        self._project = Project.instance()
        self._caseManager = CaseManager()

        # 10MB(=10,485,760=1024*1024*10)
        self._handler = RotatingFileHandler(self._project.path/'baram.log', maxBytes=10485760, backupCount=5)
        self._handler.setFormatter(logging.Formatter("[%(asctime)s][%(name)s] ==> %(message)s"))
        logging.getLogger().addHandler(self._handler)

        self._navigatorView = NavigatorView(self._ui.navigatorView)
        self._contentView = ContentView(self._ui.formView, self._ui)

        self._emptyDock = self._ui.emptyDock
        self._emptyDock.setTitleBarWidget(QWidget())
        self._renderingDock = RenderingDock(self)
        self._consoleDock = ConsoleDock(self)
        self._chartDock = ChartDock(self)
        self._monitorDock = MonitorDock(self)

        self._addTabifiedDock(self._consoleDock)
        self._addTabifiedDock(self._renderingDock)
        self._addTabifiedDock(self._chartDock)
        self._addTabifiedDock(self._monitorDock)

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

        self._closeType = CloseType.EXIT_APP

        self._meshManager = MeshManager(self)
        self._connectSignalsSlots()

        if self._caseManager.isRunning():
            self._navigatorView.setCurrentMenu(MenuItem.MENU_SOLUTION_RUN.value)
            self._chartDock.raise_()
        else:
            self._navigatorView.setCurrentMenu(MenuItem.MENU_SETUP_GENERAL.value)
            self._renderingDock.raise_()

        # self._updateMenuEnables()
        self._ui.menuMesh.setDisabled(True)
        self._ui.menuParallel.setDisabled(True)

        geometry = AppSettings.getLastMainWindowGeometry()
        display = app.qApplication.primaryScreen().availableVirtualGeometry()
        fit = getFit(geometry, display)
        self.setGeometry(fit)

    def renderingView(self):
        return self._renderingDock.view

    def case(self):
        return self._caseManager

    def tabifyDock(self, dock):
        self.tabifyDockWidget(self._emptyDock, dock)

    def load(self):
        self._project.opened()

    def closeEvent(self, event):
        if self._saveCurrentPage():
            if self._project.isModified:
                msgBox = QMessageBox()
                msgBox.setWindowTitle(self.tr("Save Changed"))
                msgBox.setText(self.tr("Do you want save your changes?"))
                msgBox.setStandardButtons(
                    QMessageBox.StandardButton.Ok
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel)
                msgBox.setDefaultButton(QMessageBox.StandardButton.Ok)

                result = msgBox.exec()
                if result == QMessageBox.StandardButton.Ok:
                    self._save()
                elif result == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
        else:
            event.ignore()
            return

        self._renderingDock.close()
        logging.getLogger().removeHandler(self._handler)
        self._handler.close()

        AppSettings.updateLastMainWindowGeometry(self.geometry())

        if self._closeType == CloseType.CLOSE_PROJECT:
            app.restart()
        else:
            app.quit()

        event.accept()

    def changeEvent(self, event):
        if event.type() == QEvent.LanguageChange:
            self._ui.retranslateUi(self)
            self._navigatorView.translate()

            for page in self._menuPages.values():
                if page.isCreated():
                    self._contentView.removePage(page)
                    page.removePage()

            self._changeForm(self._navigatorView.currentMenu())

        super().changeEvent(event)

    def vtkMeshLoaded(self):
        self._ui.menuMesh.setEnabled(True)
        self._ui.menuParallel.setEnabled(True)
        self._navigatorView.updateMenu()

    def _connectSignalsSlots(self):
        self._ui.actionSave.triggered.connect(self._save)
        self._ui.actionSaveAs.triggered.connect(self._saveAs)
        self._ui.actionOpenFoam.triggered.connect(self._loadMesh)
        self._ui.actionFluent2D.triggered.connect(self._importFluent2D)
        self._ui.actionFluent3D.triggered.connect(self._importFluent3D)
        self._ui.actionStarCCM.triggered.connect(self._importStarCcmPlus)
        self._ui.actionGmsh.triggered.connect(self._importGmsh)
        self._ui.actionIdeas.triggered.connect(self._importIdeas)
        self._ui.actionNasaPlot3d.triggered.connect(self._importNasaPlot3D)
        self._ui.actionCloseCase.triggered.connect(self._closeProject)
        self._ui.actionExit.triggered.connect(self.close)

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

        self._project.meshChanged.connect(self._meshChanged)
        self._project.projectOpened.connect(self._projectOpened)
        self._project.solverStatusChanged.connect(self._solverStatusChanged)

        self._caseManager.caseLoaded.connect(self._caseLoaded)

    def _save(self):
        if self._saveCurrentPage():
            self._project.save()

    def _saveAs(self):
        QMessageBox.information(self, self.tr('Save as a new project'),
                                self.tr('Only configuration and mesh are saved. (Calculation results are not copied)'))

        self._dialog = QFileDialog(self, self.tr('Select Project Directory'), AppSettings.getRecentLocation())
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self._dialog.finished.connect(self._projectDirectorySelected)
        self._dialog.open()

    def _saveCurrentPage(self):
        currentPage = self._contentView.currentPage()
        if currentPage:
            return currentPage.save()

        return True

    def _loadMesh(self):
        self._importMesh(MeshType.POLY_MESH)

    def _importFluent2D(self):
        self._importMesh(MeshType.FLUENT_2D, self.tr('Fluent (*.msh)'))

    def _importFluent3D(self):
        self._importMesh(MeshType.FLUENT_3D, self.tr('Fluent (*.cas)'))

    def _importStarCcmPlus(self):
        if hasUtility(self._meshManager.convertUtility(MeshType.STAR_CCM)):
            self._importMesh(MeshType.STAR_CCM, self.tr('StarCCM+ (*.ccm)'))
        else:
            QMessageBox.information(
                self, self.tr('Mesh Convert'),
                self.tr(f'Converter not found.<br>'
                        f'Install <a href="{CCM_TO_FOAM_URL}">ccmToFoam</a> to convert StarCCM+ Mesh.'
                        f'(Linux only)</a>'))

    def _importGmsh(self):
        self._importMesh(MeshType.GMSH, self.tr('Gmsh (*.msh)'))

    def _importIdeas(self):
        self._importMesh(MeshType.IDEAS, self.tr('Ideas (*.unv)'))

    def _importNasaPlot3D(self):
        self._importMesh(MeshType.NAMS_PLOT3D, self.tr('Plot3d (*.unv)'))

    def _closeProject(self):
        self._closeType = CloseType.CLOSE_PROJECT
        self.close()

    def _openMeshInfoDialog(self):
        self._dialog = MeshInfoDialog(self)
        self._dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._dialog.show()  # Call "show()" for "ApplicationModal"

    def _openMeshScaleDialog(self):
        self._dialog = MeshScaleDialog(self, self._meshManager)
        self._dialog.accepted.connect(self._scaleMesh)
        self._dialog.open()

    def _openMeshTranslateDialog(self):
        self._dialog = MeshTranslateDialog(self, self._meshManager)
        self._dialog.accepted.connect(self._translateMesh)
        self._dialog.open()

    def _openMeshRotateDialog(self):
        self._dialog = MeshRotateDialog(self, self._meshManager)
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
            if await self._meshManager.scale(*self._dialog.data()):
                progressDialog.finish(self.tr('Mesh scaling failed.'))
                return

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
            if await self._meshManager.translate(*self._dialog.data()):
                progressDialog.finish(self.tr('Mesh translation failed.'))
                return

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
            if await self._meshManager.rotate(*self._dialog.data()):
                progressDialog.finish(self.tr('Mesh rotation failed.'))
                return

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

            redistributionTask = RedistributionTask()
            redistributionTask.progress.connect(progressDialog.setLabelText)

            await redistributionTask.redistribute()

        progressDialog.finish('Parallel Environment was Applied.')

    async def _loadVtkMesh(self):
        progressDialog = ProgressDialog(self, self.tr('Case Loading.'))
        progressDialog.open()

        loader = PolyMeshLoader()
        loader.progress.connect(progressDialog.setLabelText)

        # Workaround to give some time for QT to set up timer or event loop.
        # This workaround is not necessary on Windows because BARAM for Windows
        #     uses custom-built VTK that is compiled with VTK_ALLOWTHREADS
        await asyncio.sleep(0.1)

        await loader.loadVtk()

        progressDialog.close()

    def _changeForm(self, currentMenu, previousMenu=-1):
        if previousMenu > -1:
            previousPage = self._menuPages[previousMenu]
            if previousPage and previousPage.widget == self._contentView.currentPage():
                if not previousPage.widget.save() or not previousPage.widget.checkToQuit():
                    QTimer.singleShot(0, lambda: self._navigatorView.setCurrentMenu(previousMenu))
                    return

        page = self._menuPages[currentMenu]
        if not page.isCreated():
            page.createPage(self._ui.formView)
            self._contentView.addPage(page)

        self._contentView.changePane(page)

    def _showAboutDialog(self):
        self._dialog = AboutDialog(self)
        self._dialog.open()

    def _meshChanged(self, updated):
        if self._project.meshLoaded and updated:
            targets = [
                MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value,
                MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value,
                MenuItem.MENU_SOLUTION_INITIALIZATION.value,
                MenuItem.MENU_SOLUTION_MONITORS.value,
            ]

            for page in [self._menuPages[menu] for menu in targets]:
                if page.isCreated():
                    self._contentView.removePage(page)
                    page.removePage()

            currentMenu = self._navigatorView.currentMenu()
            if currentMenu in targets:
                self._changeForm(currentMenu)

    def _solverStatusChanged(self, status):
        isSolverRunning = status == SolverStatus.RUNNING or app.case.isBatchRunning()

        self._ui.actionSaveAs.setDisabled(isSolverRunning)
        self._ui.menuLoadMesh.setDisabled(isSolverRunning)
        self._ui.menuMesh.setDisabled(isSolverRunning)
        self._ui.menuParallel.setDisabled(isSolverRunning)

        self._navigatorView.updateMenu()

    @qasync.asyncSlot()
    async def _projectOpened(self):
        if self._project.meshLoaded:
            db = coredb.CoreDB()
            if db.getRegions():
                # BaramFlow Project is opened
                await self._loadVtkMesh()
            else:
                # BaramMesh Project is opened
                progressDialog = ProgressDialog(self, self.tr('Mesh Loading'))
                progressDialog.open()

                try:
                    progressDialog.setLabelText(self.tr('Loading the boundaries.'))
                    await PolyMeshLoader().loadMesh()

                    progressDialog.close()
                except Exception as ex:
                    progressDialog.finish(self.tr('Error occurred:\n' + str(ex)))

                self._project.fileDB().saveCoreDB()

    @qasync.asyncSlot()
    async def _caseLoaded(self, name=None):
        if name:
            self.setWindowTitle(f'{app.properties.fullName} - {name} ({self._project.path})')
        else:
            self.setWindowTitle(f'{app.properties.fullName} - {self._project.path}')

    def _addTabifiedDock(self, dock):
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.tabifyDock(dock)
        self._ui.menuView.addAction(dock.toggleViewAction())

    def _changeScale(self):
        self._dialog = SettingScalingDialog(self)
        self._dialog.open()

    def _changeLanguage(self):
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

            if self._saveCurrentPage():
                progressDialog = ProgressDialog(self, self.tr('Save As'))
                progressDialog.open()

                progressDialog.setLabelText(self.tr('Saving case'))

                await asyncio.to_thread(FileSystem.saveAs, path, coredb.CoreDB().getRegions())
                self._project.saveAs(path)
                progressDialog.close()

    def _importMesh(self, meshType, fileFilter=None):
        if fileFilter is None:
            # Select OpenFOAM mesh directory.
            self._dialog = QFileDialog(self, self.tr('Select Mesh Directory'),
                                       AppSettings.getRecentMeshDirectory())
            self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        else:
            # Select a mesh file to convert.
            self._dialog = QFileDialog(self, self.tr('Select Mesh Directory'),
                                       AppSettings.getRecentMeshDirectory(), fileFilter)

        self._dialog.finished.connect(lambda result: self._meshFileSelected(result, meshType))
        self._dialog.open()

    @qasync.asyncSlot()
    async def _meshFileSelected(self, result, meshType):
        # On Windows, finishing a dialog opened with the open method does not redraw the menu bar. Force repaint.
        self._ui.menubar.repaint()

        if result != QFileDialog.DialogCode.Accepted:
            return

        file = Path(self._dialog.selectedFiles()[0])
        AppSettings.updateRecentMeshDirectory(str(file))

        if (meshType == MeshType.POLY_MESH
                and ModelsDB.isMultiphaseModelOn()
                and len(RegionProperties.loadRegions(file)) > 1
                and await AsyncMessageBox()
                        .information(self, self.tr('Permission Denied'),
                                     self.tr('Multi-region cases cannot be computed under multi-phase conditions.'))):
            return

        if not await self._confirmToReplaceMesh(True):
            return

        try:
            self._caseManager.clearCases()
        except PermissionError:
            await AsyncMessageBox().information(self, self.tr('Permission Denied'),
                                                self.tr('The project directory is open by another program.'))
            return

        self._project.setMeshLoaded(False)

        if meshType == MeshType.POLY_MESH:
            await self._meshManager.importOpenFoamMesh(file)
        else:
            await self._meshManager.importMesh(file, meshType)

        self._project.save()

    def _runParaView(self, executable, updateSetting=True):
        casePath = FileSystem.foamFilePath() if Project.instance().meshLoaded else ''
        subprocess.Popen([executable, str(casePath)])
        if updateSetting:
            AppSettings.updateParaviewInstalledPath(executable)

    async def _confirmToReplaceMesh(self, renew=False):
        if coredb.CoreDB().getRegions():
            confirm = await AsyncMessageBox().question(
                self, self.tr('Load Mesh'),
                self.tr('This action will overwrite current mesh, related configurations, and calculation data.\n'
                        'It cannot be recovered, and changed configurations will be saved automatically.'))

            if confirm != QMessageBox.StandardButton.Yes:
                return False

        return True
