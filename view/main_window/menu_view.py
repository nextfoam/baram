#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt, QCoreApplication

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

class MenuView:
    class MenuItem:
        def __init__(self, setup):
            self._text = setup["text"]
            self._pageClass = None
            self._index = -1

            if "page_class" in setup:
                self._pageClass = setup["page_class"]
            else:
                self._index = 0

        @property
        def index(self):
            return self._index

        @index.setter
        def index(self, index):
            self._index = index

        def createPage(self):
            return self._pageClass()

    def __init__(self, tree):
        self.MENU = {
            "setup": {
                "text": QCoreApplication.translate("MenuView", "Setup"),
                "sub_menu": {
                    "general": {
                        "text": QCoreApplication.translate("MenuView", "General"),
                        "page_class": GeneralPage,
                    },
                    "materials": {
                        "text": QCoreApplication.translate("MenuView", "Materials"),
                        "page_class": MaterialPage,
                    },
                    "models": {
                        "text": QCoreApplication.translate("MenuView", "Models"),
                        "page_class": ModelsPage,
                    },
                    "cellZoneConditions": {
                        "text": QCoreApplication.translate("MenuView", "Cell Zone Conditions"),
                        "page_class": CellZoneConditionsPage,
                    },
                    "boundaryConditions": {
                        "text": QCoreApplication.translate("MenuView", "Boundary Conditions"),
                        "page_class": BoundaryConditionsPage,
                    },
                    # "dynamicMesh": {
                    #     "text": QCoreApplication.translate("MenuView", "Dynamic Mesh"),
                    #     "page_class": EmptyPage,
                    # },
                    "referenceValues": {
                        "text": QCoreApplication.translate("MenuView", "Reference Values"),
                        "page_class": ReferenceValuesPage,
                    },
                },
            },
            "solution": {
                "text": QCoreApplication.translate("MenuView", "Solution"),
                "sub_menu": {
                    "numericalConditions": {
                        "text": QCoreApplication.translate("MenuView", "Numerial Conditions"),
                        "page_class": NumericalConditionsPage
                    },
                    "monitors": {
                        "text": QCoreApplication.translate("MenuView", "Monitors"),
                        "page_class": MonitorsPage
                    },
                    "initialization": {
                        "text": QCoreApplication.translate("MenuView", "Initialization"),
                        "page_class": InitializationPage
                    },
                    "runCalculation": {
                        "text": QCoreApplication.translate("MenuView", "Run Calculation"),
                        "page_class": RunCalculationPage
                    },
                },
            },
        }

        self._view = tree
        self._loadMenu()

    def connectCurrentItemChanged(self, slot):
        self._view.currentItemChanged.connect(slot)

    def paneOf(self, menuItem):
        return menuItem.data(0, Qt.UserRole)

    def paneIndex(self, menuItem):
        return self.paneOf(menuItem).index

    def currentPane(self):
        return self.paneOf(self._view.currentItem())

    def _loadMenu(self):
        for key, setup in self.MENU.items():
            item = QTreeWidgetItem(self._view)
            item.setText(0, setup["text"])
            item.setData(0, Qt.UserRole, self.MenuItem(setup))
            self._appendSubMenu(item, setup["sub_menu"])
            item.setExpanded(True)

    def _appendSubMenu(self, parent, menu):
        for key, setup in menu.items():
            item = QTreeWidgetItem(parent)
            item.setText(0, setup["text"])
            item.setData(0, Qt.UserRole, self.MenuItem(setup))

