#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QHeaderView, QTableWidgetItem, QComboBox
from PySide6.QtCore import Signal

from coredb import coredb
from coredb.boundary_db import BoundaryType, BoundaryDB
from .region_widget_ui import Ui_RegionWidget


class RegionWidget(QWidget):
    regionSelected = Signal(str)
    boundaryTypeChanged = Signal(BoundaryType)
    boundaryDoubleClicked = Signal()

    def __init__(self, rname):
        super().__init__()
        self._ui = Ui_RegionWidget()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._rname = rname

        header = self._ui.list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self._connectSignalsSlots()
        self._load()

    @property
    def rname(self):
        return self._rname

    def currentBoundaryId(self):
        return self._ui.list.item(self._ui.list.currentRow(), 0).type()

    def currentBoundaryType(self):
        return self._ui.list.cellWidget(self._ui.list.currentRow(), 1).currentData()

    def clearSelection(self):
        self._ui.list.clearSelection()

    def _load(self):
        self._ui.groupBox.setTitle(self._rname)

        boundaries = self._db.getBoundaryConditions(self._rname)

        self._ui.list.setRowCount(len(boundaries))
        i = 0
        for bcid, name, type_ in self._db.getBoundaryConditions(self._rname):
            self._ui.list.setItem(i, 0, QTableWidgetItem(name, bcid))
            self._ui.list.setCellWidget(i, 1, self._createComboBox(type_))
            i += 1

    def _connectSignalsSlots(self):
        self._ui.list.currentCellChanged.connect(self._boundarySelected)
        self._ui.list.itemDoubleClicked.connect(self._boundaryDoubleClicked)

    def _createComboBox(self, currentType):
        combo = QComboBox()

        # Inlet
        self._addComboItem(combo, currentType, BoundaryType.VELOCITY_INLET, self.tr("Velocity Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.FLOW_RATE_INLET, self.tr("Flow Rate Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.PRESSURE_INLET, self.tr("Pressure Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.ABL_INLET, self.tr("ABL Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.OPEN_CHANNEL_INLET, self.tr("Open Channel Inlet"))
        self._addComboItem(combo, currentType, BoundaryType.FREE_STREAM, self.tr("Free Stream"))
        self._addComboItem(combo, currentType, BoundaryType.FAR_FIELD_RIEMANN, self.tr("Far-Field Riemann"))
        self._addComboItem(combo, currentType, BoundaryType.SUBSONIC_INFLOW, self.tr("Subsonic Inflow"))
        self._addComboItem(combo, currentType, BoundaryType.SUPERSONIC_INFLOW, self.tr("Supersonic Inflow"))
        # Outlet, BoundaryType
        self._addComboItem(combo, currentType, BoundaryType.PRESSURE_OUTLET, self.tr("Pressure Outlet"))
        self._addComboItem(combo, currentType, BoundaryType.OPEN_CHANNEL_OUTLET, self.tr("OpenChannel Outlet"))
        self._addComboItem(combo, currentType, BoundaryType.OUTFLOW, self.tr("Outflow"))
        self._addComboItem(combo, currentType, BoundaryType.SUBSONIC_OUTFLOW, self.tr("Subsonic Outflow"))
        self._addComboItem(combo, currentType, BoundaryType.SUPERSONIC_OUTFLOW, self.tr("Supersonic Outflow"))
        # Wall, BoundaryType
        self._addComboItem(combo, currentType, BoundaryType.WALL, self.tr("Wall"))
        self._addComboItem(combo, currentType, BoundaryType.THERMO_COUPLED_WALL, self.tr("Thermo-Coupled Wall"))
        self._addComboItem(combo, currentType, BoundaryType.POROUS_JUMP, self.tr("Porous Jump"))
        self._addComboItem(combo, currentType, BoundaryType.FAN, self.tr("FAN"))
        # Internal, BoundaryType
        self._addComboItem(combo, currentType, BoundaryType.SYMMETRY, self.tr("Symmetry"))
        self._addComboItem(combo, currentType, BoundaryType.INTERFACE, self.tr("Interface"))
        self._addComboItem(combo, currentType, BoundaryType.EMPTY, self.tr("Empty"))
        self._addComboItem(combo, currentType, BoundaryType.CYCLIC, self.tr("Cyclic"))
        self._addComboItem(combo, currentType, BoundaryType.WEDGE, self.tr("Wedge"))

        combo.currentIndexChanged.connect(self._boundaryTypeChanged)

        return combo

    def _addComboItem(self, combo, current, boundaryType, text):
        combo.addItem(text, boundaryType)
        if current == boundaryType.value:
            combo.setCurrentIndex(combo.count() - 1)

    def _boundarySelected(self, row, column):
        self.regionSelected.emit(self._rname)
        self.boundaryTypeChanged.emit(self._ui.list.cellWidget(row, 1).currentData())

    def _boundaryDoubleClicked(self):
        self.boundaryDoubleClicked.emit()

    def _boundaryTypeChanged(self):
        self._db.setValue(BoundaryDB.getXPath(self.currentBoundaryId()) + '/physicalType',
                          self.currentBoundaryType().value)

        self.boundaryTypeChanged.emit(self.currentBoundaryType())
