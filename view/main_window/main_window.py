#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from PySide6.QtWidgets import QMainWindow, QWidget, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QThreadPool, Signal

from coredb.filedb import FileDB
from coredb.project import SolverStatus
from view.setup.general.general_page import GeneralPage
from view.setup.materials.material_page import MaterialPage
from view.setup.models.models_page import ModelsPage
from view.setup.cell_zone_conditions.cell_zone_conditions_page import CellZoneConditionsPage
from view.setup.boundary_conditions.boundary_conditions_page import BoundaryConditionsPage
from view.setup.reference_values.reference_values_page import ReferenceValuesPage
from view.solution.numerical_conditions.numerical_conditions_page import NumericalConditionsPage
from view.solution.monitors.monitors_page import MonitorsPage
from view.solution.initialization.initialization_page import InitializationPage
from view.solution.run_calculation.run_calculation_page import RunCalculationPage
from view.solution.process_information.process_information_page import ProcessInformationPage
from openfoam.polymesh.polymesh_loader import PolyMeshLoader
from openfoam.file_system import FileSystem
from .content_view import ContentView
from .main_window_ui import Ui_MainWindow
from .menu.settings_language import SettingLanguageDialog
from .menu.settings_scaling import SettingScalingDialog
from .navigator_view import NavigatorView, MenuItem
from .mesh_dock import MeshDock
from .console_dock import ConsoleDock
from .chart_dock import ChartDock


logger = logging.getLogger(__name__)


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
    windowClosed = Signal()

    def __init__(self, project):
        super().__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self.setWindowTitle(self.tr('Baram') + ' - ' + project.directory)
        # self._wizard = None

        self._navigatorView = NavigatorView(self._ui.navigatorView)
        self._contentView = ContentView(self._ui.formView, self._ui)

        self._emptyDock = self._ui.emptyDock
        self._emptyDock.setTitleBarWidget(QWidget())
        self._meshDock = MeshDock(self)
        self._consoleDock = ConsoleDock(self)
        self._chartDock = ChartDock(self)

        self._addDockTabified(self._consoleDock)
        self._addDockTabified(self._meshDock)
        self._addDockTabified(self._chartDock)

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
            MenuItem.MENU_SOLUTION_RUN_CALCULATION.value: MenuPage(RunCalculationPage),
            MenuItem.MENU_SOLUTION_PROCESS_INFORMATION.value: MenuPage(ProcessInformationPage),
        }

        self._project = project
        FileSystem.setup(project.directory)

        self._threadPool = QThreadPool()
        self._quit = True

        self._connectSignalsSlots()

        self.show()

    def toQuit(self):
        return self._quit

    def tabifyDock(self, dock):
        self.tabifyDockWidget(self._emptyDock, dock)

    def closeEvent(self, event):
        self.windowClosed.emit()

    def _connectSignalsSlots(self):
        self._ui.actionExit.triggered.connect(self.close)
        self._ui.actionSave.triggered.connect(self._save)
        self._ui.actionLoadMesh.triggered.connect(self._loadMesh)
        self._ui.actionCloseCase.triggered.connect(self._closeProject)
        self._navigatorView.currentMenuChanged.connect(self._changeForm)
        self._ui.actionLanguage.triggered.connect(self._changeLanguage)
        self._ui.actionScale.triggered.connect(self._changeScale)
        self._navigatorView.currentMenuChanged.connect(self._changeForm)
        self._project.statusChanged.connect(self._caseStatusChanged)

    def _closeProject(self):
        self._quit = False
        self.close()

    def _save(self):
        FileDB.save()

    def _loadMesh(self):
        dirName = QFileDialog.getExistingDirectory(self)
        if dirName:
            self._threadPool.start(lambda: self._loadOpenFoamMesh(dirName))

    def _changeForm(self, currentMenu):
        page = self._menuPages[currentMenu]
        if page.index < 0:
            newPage = page.createPage()
            page.index = self._contentView.addPage(newPage)

        self._contentView.changePane(page.index)

    def _caseStatusChanged(self, status):
        self._navigatorView.updateMenu(status)
        # self._ui.actionLoadMesh.setEnabled(status < CaseStatus.MESH_LOADED)

    def _addDockTabified(self, dock):
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.tabifyDock(dock)
        self._ui.menuView.addAction(dock.toggleViewAction())

    def _loadOpenFoamMesh(self, dirName):
        try:
            FileSystem.copyOpenFoamMeshFrom(dirName)
            PolyMeshLoader.load()
            self._project.setStatus(CaseStatus.MESH_LOADED)
        except Exception as ex:
            logger.debug(ex, exc_info=True)
            QMessageBox.critical(self, self.tr('Mesh Loading Failed'), self.tr(f'Mesh Loading Failed : {ex}'))

        self._meshDock.showOpenFoamMesh()

    def _copyMesh(self, dirName):
        FileSystem.copyOpenFoamMeshFrom(dirName)
        self._threadPool.start(lambda: PolyMeshLoader().load())
        self._threadPool.start(lambda: self._meshDock.showOpenFoamMesh())

    def _changeLanguage(self):
        self._dialogSettingLanguage = SettingLanguageDialog(self)
        self._dialogSettingLanguage.open()

    def _changeScale(self):
        self._dialogSettingScaling = SettingScalingDialog(self)
        self._dialogSettingScaling.open()
