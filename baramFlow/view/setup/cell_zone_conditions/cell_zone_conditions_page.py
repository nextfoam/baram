#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem
from vtkmodules.vtkCommonColor import vtkNamedColors

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.view.widgets.content_page import ContentPage
from .cell_zone_conditions_page_ui import Ui_CellZoneConditionsPage
from .cell_zone_condition_dialog import CellZoneConditionDialog
from .cell_zone_widget import CellZoneWidget, RegionWidget


class ListItem(QTreeWidgetItem):
    def __init__(self, parent, isRegion=False):
        super().__init__(parent)

        self._widget = None
        self._isRegion = isRegion

    def czid(self):
        return self._widget.czid()

    def isRegion(self):
        return self._isRegion

    def update(self):
        self._widget.load()

    def _setWidget(self, widget):
        self._widget = widget
        self.treeWidget().setItemWidget(self, 0, self._widget)
        self.setFirstColumnSpanned(True)


class RegionItem(ListItem):
    def __init__(self, parent):
        super().__init__(parent, True)
    
    def __lt__(self, other):
        return self._widget.rname().lower() < other._widget.rname().lower()

    def rname(self):
        return self._widget.rname()

    def setRegion(self, czid, rname):
        self._setWidget(RegionWidget(czid, rname))


class CellZoneItem(ListItem):
    def __init_(self, parent):
        super().__init__(parent)
    
    def __lt__(self, other):
        return self._widget.czname().lower() < other._widget.czname().lower()

    def rname(self):
        return self.parent().rname()

    def setCellZone(self, czid, czname):
        self._setWidget(CellZoneWidget(czid, czname))


class CellZoneConditionsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_CellZoneConditionsPage()
        self._ui.setupUi(self)

        self._ui.cellZones.setSortingEnabled(True)
        self._ui.cellZones.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        self._connectSignalsSlots()

        self._actor = None

        self._load()

    def hideEvent(self, ev):
        if not ev.spontaneous():
            if self._actor:
                view = app.renderingView
                view.removeActor(self._actor)
                view.refresh()

                self._ui.cellZones.clearSelection()
                self._actor = None

        return super().hideEvent(ev)

    def _load(self):
        regions = coredb.CoreDB().getRegions()
        if len(regions) == 1 and not regions[0]:
            self._addRegion('')
        else:
            for rname in regions:
                self._addRegion(rname)

        self._ui.cellZones.expandAll()

    def _connectSignalsSlots(self):
        self._ui.cellZones.doubleClicked.connect(self._edit)
        self._ui.cellZones.itemClicked.connect(self._cellZoneSelected)
        self._ui.edit.clicked.connect(self._edit)

    def _edit(self):
        item = self._ui.cellZones.currentItem()
        self._dialog = CellZoneConditionDialog(self, item.czid(), item.rname())
        self._dialog.accepted.connect(item.update)

        self._dialog.open()

    def _cellZoneSelected(self, item):
        view = app.renderingView
        if self._actor:
            view.removeActor(self._actor)

        if not item.isRegion():
            self._actor = app.cellZoneActor(item.czid())
            self._actor.GetProperty().SetColor(vtkNamedColors().GetColor3d('White'))
            self._actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Red'))
            self._actor.GetProperty().EdgeVisibilityOn()
            self._actor.GetProperty().SetRepresentationToSurface()
            self._actor.GetProperty().SetLineWidth(2)
            view.addActor(self._actor)

        view.refresh()

    def _addRegion(self, rname=''):
        item = RegionItem(self._ui.cellZones)

        cellZones = coredb.CoreDB().getCellZones(rname)
        for czid, czname in cellZones:
            if CellZoneDB.isRegion(czname):
                item.setRegion(czid, rname)
            else:
                child = CellZoneItem(item)
                child.setCellZone(czid, czname)
