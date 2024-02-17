#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import QObject, Signal

from baramFlow.app import app


class MenuItem(Enum):
    MENU_SETUP = QTreeWidgetItem.UserType
    MENU_SOLUTION = auto()

    # Setup
    MENU_SETUP_GENERAL = auto()
    MENU_SETUP_MODELS = auto()
    MENU_SETUP_MATERIALS = auto()
    MENU_SETUP_CELL_ZONE_CONDITIONS = auto()
    MENU_SETUP_BOUNDARY_CONDITIONS = auto()
    MENU_SETUP_REFERENCE_VALUES = auto()
    # Solution
    MENU_SOLUTION_NUMERICAL_CONDITIONS = auto()
    MENU_SOLUTION_MONITORS = auto()
    MENU_SOLUTION_INITIALIZATION = auto()
    MENU_SOLUTION_RUN_CONDITIONS = auto()
    MENU_SOLUTION_RUN = auto()


class NavigatorView(QObject):
    currentMenuChanged = Signal(int, int)

    def __init__(self, tree):
        super().__init__()

        self._view = tree

        self._menuTexts = {
            MenuItem.MENU_SETUP.value: lambda: self.tr('Setup'),
            MenuItem.MENU_SOLUTION.value: lambda: self.tr('Solution'),
            # Setup
            MenuItem.MENU_SETUP_GENERAL.value: lambda: self.tr('General'),
            MenuItem.MENU_SETUP_MODELS.value: lambda: self.tr('Models'),
            MenuItem.MENU_SETUP_MATERIALS.value: lambda: self.tr('Materials'),
            MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value: lambda: self.tr('Cell Zone Conditions'),
            MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value: lambda: self.tr('Boundary Conditions'),
            MenuItem.MENU_SETUP_REFERENCE_VALUES.value: lambda: self.tr('Reference Values'),
            # Solution
            MenuItem.MENU_SOLUTION_NUMERICAL_CONDITIONS.value: lambda: self.tr('Numerical Conditions'),
            MenuItem.MENU_SOLUTION_MONITORS.value: lambda: self.tr('Monitors'),
            MenuItem.MENU_SOLUTION_INITIALIZATION.value: lambda: self.tr('Initialization'),
            MenuItem.MENU_SOLUTION_RUN_CONDITIONS.value: lambda: self.tr('Run Conditions'),
            MenuItem.MENU_SOLUTION_RUN.value: lambda: self.tr('Run'),
        }

        self._menu = {}

        setupMenu = self._addTopMenu(MenuItem.MENU_SETUP)
        self._addMenu(MenuItem.MENU_SETUP_GENERAL, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_MODELS, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_MATERIALS, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_REFERENCE_VALUES, setupMenu)

        solutionMenu = self._addTopMenu(MenuItem.MENU_SOLUTION)
        self._addMenu(MenuItem.MENU_SOLUTION_NUMERICAL_CONDITIONS, solutionMenu)
        self._addMenu(MenuItem.MENU_SOLUTION_MONITORS, solutionMenu)
        self._addMenu(MenuItem.MENU_SOLUTION_INITIALIZATION, solutionMenu)
        self._addMenu(MenuItem.MENU_SOLUTION_RUN_CONDITIONS, solutionMenu)
        self._addMenu(MenuItem.MENU_SOLUTION_RUN, solutionMenu)

        self._connectSignalsSlots()

        self._menu[MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value].setDisabled(True)
        self._menu[MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value].setDisabled(True)
        # self.updateMenu()

    def currentMenu(self):
        return self._view.currentItem().type()

    def setCurrentMenu(self, value):
        self._view.setCurrentItem(self._menu[value])

    def updateMenu(self):
        noMesh = app.vtkMesh() is None
        solverActivated = app.solver.isActive()

        self._menu[MenuItem.MENU_SETUP_GENERAL.value].setDisabled(solverActivated)
        self._menu[MenuItem.MENU_SETUP_MODELS.value].setDisabled(solverActivated)
        self._menu[MenuItem.MENU_SETUP_MATERIALS.value].setDisabled(solverActivated)
        self._menu[MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value].setDisabled(noMesh or solverActivated)
        self._menu[MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value].setDisabled(noMesh or solverActivated)
        self._menu[MenuItem.MENU_SETUP_REFERENCE_VALUES.value].setDisabled(solverActivated)

        self._menu[MenuItem.MENU_SOLUTION_INITIALIZATION.value].setDisabled(solverActivated)
        self._menu[MenuItem.MENU_SOLUTION_RUN.value].setDisabled(noMesh)

    def translate(self):
        for key, menu in self._menu.items():
            menu.setText(0, self._menuTexts[key]())

    def _connectSignalsSlots(self):
        self._view.currentItemChanged.connect(self._currentMenuChanged)

    def _addTopMenu(self, menuItem):
        self._menu[menuItem.value] = QTreeWidgetItem(self._view, [self._menuTexts[menuItem.value]()], menuItem.value)
        self._menu[menuItem.value].setExpanded(True)

        return self._menu[menuItem.value]

    def _addMenu(self, menuItem, parent):
        self._menu[menuItem.value] = QTreeWidgetItem(parent, [self._menuTexts[menuItem.value]()], menuItem.value)

    def _currentMenuChanged(self, current, previous):
        self.currentMenuChanged.emit(current.type(), previous.type() if previous else -1)
