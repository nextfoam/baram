#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
from enum import Enum, auto

import qasync

from PySide6.QtWidgets import QMainWindow, QWidget, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QThreadPool, Signal

from coredb.project import Project
from coredb.app_settings import AppSettings
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

        self._project = Project.instance()
        self._projectChanged()

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

        self._dialog = None

        self._threadPool = QThreadPool()
        self._quit = True

        self._connectSignalsSlots()
        self._closeType = CloseType.EXIT_APP

        if self._project.meshLoaded:
            self._threadPool.start(self._meshDock.showOpenFoamMesh)

        self._updateMenuEnables()
        self.show()

    def tabifyDock(self, dock):
        self.tabifyDockWidget(self._emptyDock, dock)

    def closeEvent(self, event):
        # if self._project.isModified:
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

        Project.close()
        self.windowClosed.emit(self._closeType)
        super().closeEvent(event)

    def _connectSignalsSlots(self):
        self._ui.actionExit.triggered.connect(self.close)
        self._ui.actionSave.triggered.connect(self._save)
        self._ui.actionSaveAs.triggered.connect(self._saveAs)
        self._ui.actionLoadMesh.triggered.connect(self._loadMesh)
        self._ui.actionCloseCase.triggered.connect(self._closeProject)
        self._navigatorView.currentMenuChanged.connect(self._changeForm)
        self._ui.actionLanguage.triggered.connect(self._changeLanguage)
        self._ui.actionScale.triggered.connect(self._changeScale)
        self._navigatorView.currentMenuChanged.connect(self._changeForm)
        self._project.statusChanged.connect(self._updateMenuEnables)
        self._project.projectChanged.connect(self._projectChanged)

    def _closeProject(self):
        self._closeType = CloseType.CLOSE_PROJECT
        self.close()

    def _save(self):
        self._saveCurrentPage()
        self._project.save()

    def _saveAs(self):
        self._saveCurrentPage()
        # dirName = QFileDialog.getExistingDirectory(self, self.tr('Case Directory'), AppSettings.getRecentDirectory())
        # if dirName:
        dirName = QFileDialog.getSaveFileName(self, self.tr('Case Directory'), AppSettings.getRecentLocation())[0]
        if dirName:
            if os.path.exists(dirName):
                if not os.path.isdir(dirName):
                    QMessageBox.critical(self, self.tr('Case Directory Error'), self.tr(f'{dirName} is not a directory.'))
                    return
                elif os.listdir(dirName):
                    QMessageBox.critical(self, self.tr('Case Directory Error'), self.tr(f'{dirName} is not empty.'))
                    return

            self._project.saveAs(dirName)

    def _saveCurrentPage(self):
        currentPage = self._contentView.currentPage()
        if currentPage:
            currentPage.save()

    def _loadMesh(self):
        # dirName = QFileDialog.getExistingDirectory(self)
        self._dialog = QFileDialog(self)
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.accepted.connect(self._meshFilesSelected)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _meshFilesSelected(self):
        if dirs := self._dialog.selectedFiles():
            await self._loadOpenFoamMesh(dirs[0])

    def _changeForm(self, currentMenu):
        page = self._menuPages[currentMenu]
        if page.index < 0:
            newPage = page.createPage()
            page.index = self._contentView.addPage(newPage)

        self._contentView.changePane(page.index)

    def _updateMenuEnables(self):
        self._navigatorView.updateMenu()
        self._ui.actionLoadMesh.setEnabled(not self._project.meshLoaded)

    def _projectChanged(self):
        self.setWindowTitle(f'{self.tr("Baram")} - {self._project.path}')
        FileSystem.setup()

    def _addDockTabified(self, dock):
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.tabifyDock(dock)
        self._ui.menuView.addAction(dock.toggleViewAction())

    async def _loadOpenFoamMesh(self, dirName):
        try:
            self._ui.actionLoadMesh.setEnabled(False)
            await FileSystem.copyMeshFrom(dirName)
            PolyMeshLoader.load()
            self._project.setMeshLoaded()
        except Exception as ex:
            logger.debug(ex, exc_info=True)
            QMessageBox.critical(self, self.tr('Mesh Loading Failed'), self.tr(f'Mesh Loading Failed.'))
            self._ui.actionLoadMesh.setEnabled(True)
            return

        self._meshDock.showOpenFoamMesh()

    def _changeLanguage(self):
        self._dialogSettingLanguage = SettingLanguageDialog(self)
        self._dialogSettingLanguage.open()

    def _changeScale(self):
        self._dialogSettingScaling = SettingScalingDialog(self)
        self._dialogSettingScaling.open()
