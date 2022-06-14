#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from .cell_zone_conditions_page_ui import Ui_CellZoneConditionsPage
from .region_widget import RegionWidget
from .operating_conditions_dialog import OperatingConditionsDialog
from .cell_zone_condition_dialog import CellZoneConditionDialog
from .cell_zone_db import CellZoneDB


class CellZoneConditionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_CellZoneConditionsPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._regions = {}
        self._currentRegion = None

        self._connectSignalsSlots()
        self._load()

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        materials = self._db.getMaterials()
        for name, region in self._regions.items():
            region.setMaterials(materials)

        return super().showEvent(ev)

    def hideEvent(self, ev):
        if ev.spontaneous():
            return super().hideEvent(ev)

        writer = CoreDBWriter()
        for name, region in self._regions.items():
            writer.append(CellZoneDB.getRegionXPath(name) + '/material', str(region.material()), None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().hideEvent(ev)

        return super().hideEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.operatingConditions.clicked.connect(self._operatingConditions)
        self._ui.edit.clicked.connect(self._edit)

    def _load(self):
        layout = self._ui.regions.layout()
        regions = self._db.getRegions()
        for r in regions:
            self._regions[r] = RegionWidget(r)
            layout.addWidget(self._regions[r])
            self._regions[r].regionSelected.connect(self._regionSelected)
            self._regions[r].cellZoneDoubleClicked.connect(self._edit)

    def _regionSelected(self, rname):
        if rname == self._currentRegion:
            return

        if self._currentRegion is not None:
            self._regions[self._currentRegion].clearSelection()

        self._currentRegion = rname
        self._ui.edit.setEnabled(True)

    def _operatingConditions(self):
        self._dialog = OperatingConditionsDialog(self)
        self._dialog.open()

    def _edit(self):
        self._dialog = CellZoneConditionDialog(self, self._currentRegion,
                                               self._regions[self._currentRegion].currentCellZone())
        self._dialog.open()
