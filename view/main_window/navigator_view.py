#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import QObject, Signal

from coredb.project import Project, SolverStatus


class MenuItem(Enum):
    MENU_TOP = QTreeWidgetItem.UserType
    # Setup
    MENU_SETUP_GENERAL = auto()
    MENU_SETUP_MATERIALS = auto()
    MENU_SETUP_MODELS = auto()
    MENU_SETUP_CELL_ZONE_CONDITIONS = auto()
    MENU_SETUP_BOUNDARY_CONDITIONS = auto()
    MENU_SETUP_REFERENCE_VALUES = auto()
    # Solution
    MENU_SOLUTION_NUMERICAL_CONDITIONS = auto()
    MENU_SOLUTION_MONITORS = auto()
    MENU_SOLUTION_INITIALIZATION = auto()
    MENU_SOLUTION_RUN_CALCULATION = auto()
    MENU_SOLUTION_PROCESS_INFORMATION = auto()


class NavigatorView(QObject):
    currentMenuChanged = Signal(int)

    def __init__(self, tree):
        super().__init__()

        self._view = tree
        
        self._setupMenu = self._addTopMenu(self.tr('Setup'))
        self._solutionMenu = self._addTopMenu(self.tr('Solution'))

        self._menu = {}
        self._addMenu(MenuItem.MENU_SETUP_GENERAL, self._setupMenu,
                      self.tr('General'))
        self._addMenu(MenuItem.MENU_SETUP_MATERIALS, self._setupMenu,
                      self.tr('Materials'))
        self._addMenu(MenuItem.MENU_SETUP_MODELS, self._setupMenu,
                      self.tr('Models'))
        self._addMenu(MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS, self._setupMenu,
                      self.tr('Cell Zone Conditions'))
        self._addMenu(MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS, self._setupMenu,
                      self.tr('Boundary Conditions'))
        self._addMenu(MenuItem.MENU_SETUP_REFERENCE_VALUES, self._setupMenu,
                      self.tr('Reference Values'))
        self._addMenu(MenuItem.MENU_SOLUTION_NUMERICAL_CONDITIONS, self._solutionMenu,
                      self.tr('Numerical Conditions'))
        self._addMenu(MenuItem.MENU_SOLUTION_MONITORS, self._solutionMenu,
                      self.tr('Monitors'))
        self._addMenu(MenuItem.MENU_SOLUTION_INITIALIZATION, self._solutionMenu,
                      self.tr('Initialization'))
        self._addMenu(MenuItem.MENU_SOLUTION_RUN_CALCULATION, self._solutionMenu,
                      self.tr('Calculate Conditions'))
        self._addMenu(MenuItem.MENU_SOLUTION_PROCESS_INFORMATION, self._solutionMenu,
                      self.tr('Run Calculation'))

        self._connectSignalsSlots()
        self.updateMenu()

    def currentMenu(self):
        return self._view.currentItem().type()

    def setCurrentMenu(self, menuItem):
        self._view.setCurrentItem(self._menu[menuItem.value])

    def updateMenu(self):
        project = Project.instance()
        noMesh = not project.meshLoaded
        solverSubmitted = project.solverStatus() != SolverStatus.NONE

        self._menu[MenuItem.MENU_SETUP_GENERAL.value].setDisabled(solverSubmitted)
        self._menu[MenuItem.MENU_SETUP_MATERIALS.value].setDisabled(solverSubmitted)
        self._menu[MenuItem.MENU_SETUP_MODELS.value].setDisabled(solverSubmitted)
        self._menu[MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value].setDisabled(noMesh or solverSubmitted)
        self._menu[MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value].setDisabled(noMesh or solverSubmitted)
        self._menu[MenuItem.MENU_SETUP_REFERENCE_VALUES.value].setDisabled(solverSubmitted)

        self._menu[MenuItem.MENU_SOLUTION_INITIALIZATION.value].setDisabled(solverSubmitted)
        self._menu[MenuItem.MENU_SOLUTION_PROCESS_INFORMATION.value].setDisabled(noMesh)

    def _connectSignalsSlots(self):
        self._view.currentItemChanged.connect(self._currentMenuChanged)

    def _addTopMenu(self, text):
        item = QTreeWidgetItem(self._view, [text], MenuItem.MENU_TOP.value)
        item.setExpanded(True)
        return item

    def _addMenu(self, key, parent, text):
        self._menu[key.value] = QTreeWidgetItem(parent, [text], key.value)

    def _currentMenuChanged(self, current):
        self.currentMenuChanged.emit(current.type())
