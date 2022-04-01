#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt

from view.pane.empty_pane import EmptyPane
from view.pane.general_pane import GeneralPane
from view.pane.models_pane import ModelsPane


class MenuView:
    MENU = {
        "setup" : {
            "text": "Setup",
            "pane_class": EmptyPane,
            "sub_menu": {
                "general": {
                    "text": "General",
                    "pane_class": GeneralPane,
                },
                "models": {
                    "text": "Models",
                    "pane_class": ModelsPane,
                },
                "materials": {
                    "text": "Materials",
                    "pane_class": EmptyPane,
                },
                "cellZoneConditions": {
                    "text": "Cell Zone Conditions",
                    "pane_class": EmptyPane,
                },
                "boundayConditions": {
                    "text": "Boundary Conditions",
                    "pane_class": EmptyPane,
                },
                "dynamicMesh": {
                    "text": "Dynamic Mesh",
                    "pane_class": EmptyPane,
                },
                "referenceValues": {
                    "text": "Reference Values",
                    "pane_class": EmptyPane,
                },
            }
        }
    }

    class MenuItem:
        def __init__(self, setup):
            self._pane = None
            self._text = setup["text"]
            self._paneClass = setup["pane_class"]

        @property
        def paneClass(self):
            return self._paneClass

        @property
        def pane(self):
            if self._pane is None:
                self._pane = self._paneClass()

            return self._pane

    def __init__(self, tree):
        self._ui = tree
        self._loadMenu()

    def connectCurrentItemChanged(self, slot):
        self._ui.currentItemChanged.connect(slot)

    def paneOf(self, menuItem):
        return menuItem.data(0, Qt.UserRole).pane

    def currentPane(self):
        return self.paneOf(self._ui.currentItem())

    def _loadMenu(self):
        for key, setup in self.MENU.items():
            item = QTreeWidgetItem(self._ui)
            item.setText(0, setup["text"])
            item.setData(0, Qt.UserRole, self.MenuItem(setup))
            self._appendSubMenu(item, setup["sub_menu"])
            item.setExpanded(True)

    def _appendSubMenu(self, parent, menu):
        for key, setup in menu.items():
            item = QTreeWidgetItem(parent)
            item.setText(0, setup["text"])
            item.setData(0, Qt.UserRole, self.MenuItem(setup))

