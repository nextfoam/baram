#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from view.setup.cell_zone_conditions.cell_zone_conditions_page_ui import Ui_CellZoneConditionsPage
from .region_widget import RegionWidget
from .operating_conditions_dialog import OperatingConditionsDialog
from .cell_zone_condition_dialog import CellZoneConditionDialog


class CellZoneConditionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_CellZoneConditionsPage()
        self._ui.setupUi(self)

        self._regions = {}
        self._currentRegion = None
        self._regionsLayout = self._ui.regions.layout()

        self._connectSignalsSlots()

    def load(self):
        regions = [
            {
                "id": "r1",
                "name": "region1",
                "cellZones": {"zone1-1", "zone1-2"}
            },
            {
                "id": "r2",
                "name": "region2",
                "cellZones": {"zone2-1", "zone2-2"}
            },
        ]

        for region in regions:
            self._addRegion(region)

    def save(self):
        pass

    def regionSelected(self, regionId):
        self._currentRegion = regionId

        for key, item in self._regions.items():
            if key != regionId:
                item.clearSelection()

        self._ui.operatingConditions.setEnabled(True)
        self._ui.edit.setEnabled(True)

    def edit(self):
        dialog = CellZoneConditionDialog()
        dialog.exec()

    def _connectSignalsSlots(self):
        self._ui.operatingConditions.clicked.connect(self._operatingConditions)
        self._ui.edit.clicked.connect(self.edit)

    def _addRegion(self, region):
        id_ = region["id"]
        self._regions[id_] = RegionWidget(self, region)
        self._regionsLayout.addWidget(self._regions[id_])

    def _operatingConditions(self):
        dialog = OperatingConditionsDialog()
        dialog.exec()
