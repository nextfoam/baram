#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QMessageBox, QTreeWidgetItem, QComboBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.region_db import RegionDB
from coredb.project import Project
from .cell_zone_conditions_page_ui import Ui_CellZoneConditionsPage
from .operating_conditions_dialog import OperatingConditionsDialog
from .cell_zone_condition_dialog import CellZoneConditionDialog
from .cell_zone_widget import CellZoneWidget


DEFAULT_REGION_NAME = 'region0'


class CellZoneConditionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_CellZoneConditionsPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._singleRegion = False

        self._connectSignalsSlots()

        self.load()

    def hideEvent(self, ev):
        if not ev.spontaneous():
            self.save()

        return super().hideEvent(ev)

    def save(self):
        writer = CoreDBWriter()
        for i in range(self._ui.cellZones.topLevelItemCount()):
            rname, combo = self._region(i)
            writer.append(RegionDB.getXPath(rname) + '/material', str(combo.currentData()), None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())

    def load(self):
        regions = self._db.getRegions()
        if len(regions) == 1 and not regions[0]:
            self._singleRegion = True
            item = QTreeWidgetItem(self._ui.cellZones, [DEFAULT_REGION_NAME], 0)
            self._ui.cellZones.setItemWidget(item, 1, QComboBox())
            self._addCellZones(item, '')
        else:
            self._singleRegion = False
            for rname in regions:
                item = QTreeWidgetItem(self._ui.cellZones, [rname], 0)
                self._ui.cellZones.setItemWidget(item, 1, QComboBox())
                self._addCellZones(item, rname)

        self._ui.cellZones.expandAll()
        self._setupMaterials()

    def clear(self):
        self._ui.cellZones.clear()

    def _connectSignalsSlots(self):
        self._ui.operatingConditions.clicked.connect(self._operatingConditions)
        self._ui.cellZones.doubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)
        Project.instance().materialChanged.connect(self._setupMaterials)

    def _setupMaterials(self):
        materials = self._db.getMaterials()
        regionCount = self._ui.cellZones.topLevelItemCount()
        for i in range(regionCount):
            rname, combo = self._region(i)
            material = RegionDB.getMaterial(rname)
            combo.clear()
            for mid, name, formula, phase in materials:
                combo.addItem(name, mid)
                if mid == int(material):
                    combo.setCurrentText(name)

    def _operatingConditions(self):
        self._dialog = OperatingConditionsDialog(self)
        self._dialog.open()

    def _edit(self):
        czid = self._ui.cellZones.currentItem().type()
        if czid:
            self._dialog = CellZoneConditionDialog(self, czid)
            self._dialog.open()

    def _addCellZones(self, parent, rname):
        cellZones = self._db.getCellZones(rname)
        for czid, czname in cellZones:
            item = QTreeWidgetItem(parent, czid)
            cellZoneWidget = CellZoneWidget(czid, czname)
            self._ui.cellZones.setItemWidget(item, 0, cellZoneWidget)
            item.setFirstColumnSpanned(True)

    def _region(self, index):
        item = self._ui.cellZones.topLevelItem(index)
        return '' if self._singleRegion else item.text(0),  self._ui.cellZones.itemWidget(item, 1)
