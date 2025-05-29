#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

from baramFlow.coredb.cell_zone_db import ZoneType, CellZoneDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME, RegionDB
from .cell_zone_widget_ui import Ui_CellZoneWidget


class CellZoneWidget(QWidget):
    def __init__(self, czid, czname):
        super().__init__()
        self._ui = Ui_CellZoneWidget()
        self._ui.setupUi(self)

        self._types = {
            ZoneType.NONE: self.tr('None'),
            ZoneType.MRF: self.tr('Multiple Reference Frame'),
            ZoneType.POROUS: self.tr('Porous Zone'),
            ZoneType.SLIDING_MESH: self.tr('Sliding Mesh'),
            ZoneType.ACTUATOR_DISK: self.tr('Actuator Disk'),
        }

        self._czid = czid

        self._ui.name.setText(czname)
        self.load()

    def czid(self):
        return self._czid
    
    def czname(self):
        return self._ui.name.text()

    def load(self):
        self._ui.type.setText(self._types[CellZoneDB.getCellZoneType(self._czid)])


class RegionWidget(QWidget):
    def __init__(self, czid, rname=None):
        super().__init__()
        self._ui = Ui_CellZoneWidget()
        self._ui.setupUi(self)

        self._czid = czid
        self._rname = rname

        self._ui.name.setText( rname if rname else DEFAULT_REGION_NAME)
        self.load()

    def czid(self):
        return self._czid

    def rname(self):
        return self._rname

    def load(self):
        self._ui.type.setText(MaterialDB.getName(RegionDB.getMaterial(self._rname)))
