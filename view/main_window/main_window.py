#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler
import os
from enum import Enum, auto
from pathlib import Path

import qasync
import asyncio

from PySide6.QtWidgets import QMainWindow, QWidget, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtGui import QIcon

from app import app
from coredb.project import Project
from coredb.app_settings import AppSettings
from coredb import coredb
from resources import resource
from view.setup.general.general_page import GeneralPage
from view.setup.materials.material_page import MaterialPage
from view.setup.models.models_page import ModelsPage
from view.setup.cell_zone_conditions.cell_zone_conditions_page import CellZoneConditionsPage
from view.setup.boundary_conditions.boundary_conditions_page import BoundaryConditionsPage
from view.setup.reference_values.reference_values_page import ReferenceValuesPage
from view.solution.numerical_conditions.numerical_conditions_page import NumericalConditionsPage
from view.solution.monitors.monitors_page import MonitorsPage
from view.solution.initialization.initialization_page import InitializationPage
from view.solution.run_conditions.run_conditions_page import RunConditionsPage
from view.solution.run.process_information_page import ProcessInformationPage
from view.main_window.menu.mesh.mesh_scale_dialog import MeshScaleDialog
from view.main_window.menu.mesh.mesh_translate_dialog import MeshTranslateDialog
from view.main_window.menu.mesh.mesh_rotate_dialog import MeshRotateDialog
from view.main_window.menu.settings_language import SettingLanguageDialog
from view.widgets.progress_dialog import ProgressDialog
from mesh.mesh_manager import MeshManager, MeshType
from openfoam.file_system import FileSystem
from openfoam.case_generator import CaseGenerator
from openfoam.polymesh.polymesh_loader import PolyMeshLoader
from openfoam.run import hasUtility
from .content_view import ContentView
from .main_window_ui import Ui_MainWindow
from .menu.settings_scaling import SettingScalingDialog
from .navigator_view import NavigatorView, MenuItem
from .mesh_dock import MeshDock
from .console_dock import ConsoleDock
from .chart_dock import ChartDock
from .monitor_dock import MonitorDock


logger = logging.getLogger(__name__)

CCM_TO_FOAM_URL = 'https://openfoamwiki.net/index.php/Ccm26ToFoam'


class CloseType(Enum):
    EXIT_APP = 0
    CLOSE_PROJECT = auto()


class MenuPage:
    def __init__(self, pageClass=None):
        self._pageClass = pageClass
        self._index = -1 if pageClass else 0

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, index):
        self._index = index

    def createPage(self):
        return self._pageClass()


class MainWindow(QMainWindow):
    windowClosed = Signal(CloseType)

    def __init__(self):
        super().__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self.setWindowIcon(QIcon(str(resource.file('baram.ico'))))

        self._project = Project.instance()
        self._projectChanged()
        FileSystem.setupForProject()

        # 10MB(=10,485,760=1024*1024*10)
        self._handler = RotatingFileHandler(self._project.path/'baram.log', maxBytes=10485760, backupCount=5)
        self._handler.setFormatter(logging.Formatter("[%(asctime)s][%(name)s] ==> %(message)s"))
        logging.getLogger().addHandler(self._handler)

        self._navigatorView = NavigatorView(self._ui.navigatorView)
        self._contentView = ContentView(self._ui.formView, self._ui)

        self._emptyDock = self._ui.emptyDock
        self._emptyDock.setTitleBarWidget(QWidget())
        self._meshDock = MeshDock(self)
        self._consoleDock = ConsoleDock(self)
        self._chartDock = ChartDock(self)
        self._monitorDock = MonitorDock(self)

        self._addTabifiedDock(self._consoleDock)
        self._addTabifiedDock(self._meshDock)
        self._addTabifiedDock(self._chartDock)
        self._addTabifiedDock(self._monitorDock)

        self._menuPages = {
            MenuItem.MENU_TOP.value: MenuPage(),
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

        self._threadPool = QThreadPool()
        self._quit = True

        self._closeType = CloseType.EXIT_APP

        self._meshManager = MeshManager(self)
        self._connectSignalsSlots()

        if self._project.meshLoaded:
            self._meshManager.meshChanged.emit()

        if self._project.isSolverRunning():
            self._navigatorView.setCurrentMenu(MenuItem.MENU_SOLUTION_RUN)
            self._chartDock.raise_()
        else:
            self._navigatorView.setCurrentMenu(MenuItem.MENU_SETUP_GENERAL)
            self._meshDock.raise_()

        self._project.opened()

        # self._updateMenuEnables()
        self._ui.menuMesh.setDisabled(True)
        self.show()

    def tabifyDock(self, dock):
        self.tabifyDockWidget(self._emptyDock, dock)

    def closeEvent(self, event):
        if self._saveCurrentPage():
            if self._project.isModified:
                msgBox = QMessageBox()
                msgBox.setWindowTitle(self.tr("Save Changed"))
                msgBox.setText(self.tr("Do you want save your changes?"))
                msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Discard | QMessageBox.Cancel)
                msgBox.setDefaultButton(QMessageBox.Ok)

                result = msgBox.exec()
                if result == QMessageBox.Ok:
                    self._save()
                elif result == QMessageBox.Cancel:
                    event.ignore()
                    return
        else:
            event.ignore()
            return

        logging.getLogger().removeHandler(self._handler)

        app.close()
        event.accept()
        self.windowClosed.emit(self._closeType)

    def meshDock(self):
        return self._meshDock

    def vtkMeshLoaded(self):
        self._ui.menuMesh.setEnabled(True)
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

        self._ui.actionMeshScale.triggered.connect(self._scaleMesh)
        self._ui.actionMeshTranslate.triggered.connect(self._translateMesh)
        self._ui.actionMeshRotate.triggered.connect(self._rotateMesh)

        self._ui.actionScale.triggered.connect(self._changeScale)
        self._ui.actionLanguage.triggered.connect(self._changeLanguage)
        self._navigatorView.currentMenuChanged.connect(self._changeForm)

        self._project.meshChanged.connect(self._meshChanged)
        self._project.solverStatusChanged.connect(self._updateMenuEnables)
        self._project.projectOpened.connect(self._projectChanged)
        self._meshManager.meshChanged.connect(self._vtkChanged, Qt.ConnectionType.QueuedConnection)

    def _save(self):
        if self._saveCurrentPage():
            FileSystem.save()
            self._project.save()

    def _saveAs(self):
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
                        f'Install <a href="{CCM_TO_FOAM_URL}">ccn26ToFoam</a> to convert StarCCM+ Mesh.'
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

    def _scaleMesh(self):
        self._dialog = MeshScaleDialog(self, self._meshManager)
        self._dialog.open()

    def _translateMesh(self):
        self._dialog = MeshTranslateDialog(self, self._meshManager)
        self._dialog.open()

    def _rotateMesh(self):
        self._dialog = MeshRotateDialog(self, self._meshManager)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _vtkChanged(self):
        progress = ProgressDialog(self, self.tr('Case Loading.'), self.tr('Loading Mesh.'))

        # Workaround to give some time for QT to set up timer or event loop.
        # This workaround is not necessary on Windows because BARAM for Windows
        #     uses custom-built VTK that is compiled with VTK_ALLOWTHREADS
        await asyncio.sleep(0.1)

        await PolyMeshLoader().loadVtk()

        self.vtkMeshLoaded()
        progress.close()

    def _changeForm(self, currentMenu):
        page = self._menuPages[currentMenu]
        if page.index < 0:
            newPage = page.createPage()
            page.index = self._contentView.addPage(newPage)

        self._contentView.changePane(page.index)

    def _meshChanged(self, updated):
        # self._updateMenuEnables()
        if self._project.meshLoaded and updated:
            self._clearPage(MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS)
            self._clearPage(MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS)
            self._clearPage(MenuItem.MENU_SOLUTION_MONITORS)
            self._loadPage(MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS)
            self._loadPage(MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS)

    def _updateMenuEnables(self):
        # self._ui.menuMesh.setEnabled(self._project.meshLoaded)
        self._navigatorView.updateMenu()

    def _projectChanged(self):
        self.setWindowTitle(f'{self.tr("Baram")} - {self._project.path}')

    def _addTabifiedDock(self, dock):
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.tabifyDock(dock)
        self._ui.menuView.addAction(dock.toggleViewAction())

    def _changeScale(self):
        self._dialogSettingScaling = SettingScalingDialog(self)
        self._dialogSettingScaling.open()

    def _changeLanguage(self):
        self._dialogSettingLanguage = SettingLanguageDialog(self)
        self._dialogSettingLanguage.open()

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
            path.mkdir(exist_ok=True)

            if self._saveCurrentPage():
                progress = ProgressDialog(self, self.tr('Save As'), self.tr('Saving case'))
                await asyncio.to_thread(FileSystem.saveAs, path)
                self._project.saveAs(path)
                progress.close()

    def _clearPage(self, menu):
        page = self._menuPages[menu.value]
        if page.index > 0:
            self._contentView.page(page.index).clear()

    def _loadPage(self, menu):
        page = self._menuPages[menu.value]
        if page.index > 0:
            self._contentView.page(page.index).load()

    def _importMesh(self, meshType, fileFilter=None):
        if coredb.CoreDB().getRegions():
            confirm = QMessageBox.question(
                self, self.tr('Load Mesh'),
                self.tr('Current mesh and monitor configurations will be cleared.\n'
                        'Would you like to load another mesh?'))

            if confirm != QMessageBox.Yes:
                return

        self._project.setMeshLoaded(False)
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

        if result == QFileDialog.Accepted:
            CaseGenerator.createCase()

            file = Path(self._dialog.selectedFiles()[0])
            AppSettings.updateRecentMeshDirectory(str(file))
            if meshType == MeshType.POLY_MESH:
                await self._meshManager.importOpenFoamMesh(file)
            else:
                await self._meshManager.importMesh(file, meshType)
