#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QLabel, QWidget, QVBoxLayout, QComboBox, QRadioButton, QButtonGroup
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QGridLayout

from widgets.async_message_box import AsyncMessageBox
from widgets.flat_push_button import FlatPushButton
from widgets.typed_edit import IdentifierEdit

from baramFlow.openfoam.constant.cell_zones_to_regions import CellZonesToRegions

from .fluent_regions_dialog_ui import Ui_FlluentRegionsDialog

removeIcon = QIcon(':/icons/trash-outline.svg')

HEADER_ROW = 0
COLUMN_HEADER_ROW = 0
CELL_ZONE_START_ROW = 1

RESERVED_NAMES = ['region0']

class RegionHeader(QWidget):
    def __init__(self, name, phase):
        super().__init__()

        self._name = IdentifierEdit(name)
        self._phase = QComboBox()

        self._phase.addItems(['Fluid', 'Solid'])
        if phase == 'solid':
            self._phase.setCurrentText('Solid')

        layout = QVBoxLayout(self)
        layout.addWidget(self._name)
        layout.addWidget(self._phase)

    def name(self):
        return self._name.text().strip()

    def phase(self):
        return 'solid' if self._phase.currentText() == 'Solid' else 'fluid'


class CellZones:
    def __init__(self):
        self._cznames = []
        self._buttonGroups = []

        for i in range(CELL_ZONE_START_ROW):
            self._cznames.append(None)
            self._buttonGroups.append(None)

    def append(self, czname):
        self._cznames.append(czname)
        self._buttonGroups.append(QButtonGroup())

    def addRadio(self, row, radio):
        self._buttonGroups[row].addButton(radio)

    def czname(self, row):
        return self._cznames[row]

    def cznames(self):
        return self._cznames[CELL_ZONE_START_ROW:]

    def rowsRange(self):
        return range(CELL_ZONE_START_ROW, len(self._cznames))


class RegionColumn(QObject):
    removeClicked = Signal(int)

    def __init__(self, index, name, phase, rowCount):
        super().__init__()

        self._index = index
        self._rows = [RegionHeader(name, phase)]
        self._hidden = False

        for i in range(CELL_ZONE_START_ROW, rowCount):
            radio = QRadioButton()
            radio.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._rows.append(radio)

        button = FlatPushButton(removeIcon, '')
        button.clicked.connect(lambda: self.removeClicked.emit(self._index))
        self._rows.append(button)

    def header(self):
        return self._rows[0]

    def radio(self, row):
        return self._rows[row]

    def removeButton(self):
        return self._rows[-1]

    def check(self, row):
        self._rows[row].setChecked(True)

    def isChecked(self, row):
        return self._rows[row].isChecked()

    def name(self):
        return None if self._hidden else self.header().name()

    def phase(self):
        return self.header().phase()

    def hide(self):
        for widget in self._rows:
            widget.hide()
            self._hidden = True

    def isHidden(self):
        return self._hidden


class FluentRegionsDialog(QDialog):
    def __init__(self, parent, cellZones):
        super().__init__(parent)
        self._ui = Ui_FlluentRegionsDialog()
        self._ui.setupUi(self)

        # Start with layout index of first cell zone, will be increased as count of cell zones
        self._rowCount = CELL_ZONE_START_ROW
        self._cellZones = CellZones()
        # Add a dummy column to match the index to the layout index.
        self._columns = [RegionColumn(0, None, None, 0)]

        self._table: QGridLayout = self._ui.table.layout()

        self._connectSignalsSlots()

        regions = {'fluid': [], 'solid': []}

        for czname, phase in cellZones.items():
            self._table.addWidget(QLabel(czname), self._rowCount, COLUMN_HEADER_ROW)
            regions[phase].append(self._rowCount)
            self._cellZones.append(czname)
            self._rowCount += 1

        for phase, rows in regions.items():
            column = self._addColumn(phase)
            for r in rows:
                column.check(r)

        self._columns[1].removeButton().hide()

    def _connectSignalsSlots(self):
        self._ui.addRegion.clicked.connect(self._addColumn)
        self._ui.ok.clicked.connect(self._accept)

    def _addColumn(self, phase='fluid'):
        def nameExists(name):
            for col in self._columns:
                if name == col.name():
                    return True

            return False

        seq = 1
        rname = 'region1'
        while nameExists(rname):
            seq += 1
            rname = f'region{seq}'


        index = self._table.columnCount()
        column = RegionColumn(index, rname, phase, self._rowCount)
        column.removeClicked.connect(self._removeColumn)
        self._columns.append(column)

        self._table.addWidget(column.header(), 0, index)
        for i in range(1, self._rowCount):
            radio = column.radio(i)
            self._table.addWidget(radio, i, index, Qt.AlignmentFlag.AlignCenter)
            self._cellZones.addRadio(i, radio)

        self._table.addWidget(column.removeButton(), self._rowCount, index)

        return column

    def _removeColumn(self, index):
        target = self._columns[index]
        index -= 1
        while self._columns[index].isHidden():
            index -= 1

        substitute = self._columns[index]
        for i in self._cellZones.rowsRange():
            if target.isChecked(i):
                substitute.check(i)

        target.hide()

    @qasync.asyncSlot()
    async def _accept(self):
        cellZones = {self._cellZones.czname(i): 'fluid' for i in self._cellZones.rowsRange()}
        regions = {}

        for col in self._columns[1:]:
            rname = col.name()
            if rname in RESERVED_NAMES:
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('{} is an unavailable region name').format(rname))
                return
            if not col.isHidden():
                regionCellZones = []
                for i in self._cellZones.rowsRange():
                    if col.isChecked(i):
                        czname = self._cellZones.czname(i)
                        regionCellZones.append(czname)
                        cellZones[czname] = col.phase()

                if regionCellZones:
                    regions[rname] = {
                        'cellZones': regionCellZones,
                        'type': col.phase()
                    }

        CellZonesToRegions().setCellZoneRegions(cellZones, regions).write()

        self.accept()



