#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, QPoint

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import ZoneType, CellZoneDB
from .cell_zone_widget_ui import Ui_CellZoneWidget


class CellZoneWidget(QWidget):
    rightClicked = Signal(int, QPoint)

    def __init__(self, czid, czname):
        super().__init__()
        self._ui = Ui_CellZoneWidget()
        self._ui.setupUi(self)

        self._types = {
            ZoneType.NONE.value: self.tr('None'),
            ZoneType.MRF.value: self.tr('Multiple Refernce Frame'),
            ZoneType.POROUS.value: self.tr('Porous Zone'),
            ZoneType.SLIDING_MESH.value: self.tr('Sliding Mesh'),
            ZoneType.ACTUATOR_DISK.value: self.tr('Actuator Disk'),
        }

        self._db = coredb.CoreDB()

        self._czid = czid

        self._ui.name.setText(czname)
        self.updateType()

    def updateType(self):
        self._ui.type.setText(self._types[CellZoneDB.getCellZoneType(self._czid)])
