#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

import qasync
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QLabel, QWidget, QComboBox, QRadioButton, QButtonGroup, QFrame
from PySide6.QtWidgets import QVBoxLayout, QGridLayout

from widgets.async_message_box import AsyncMessageBox
from widgets.flat_push_button import FlatPushButton
from widgets.typed_edit import IdentifierEdit

from baramFlow.openfoam.constant.cell_zones_to_regions import CellZonesToRegions

from .fluent_regions_dialog_ui import Ui_FlluentRegionsDialog

removeIcon = QIcon(':/icons/trash-outline.svg')

HEADER_ROW = 0
COLUMN_HEADER_ROW = 0
CELL_ZONE_START_ROW = 1

# Gap between the frozen cell zone name column and the radio buttons next to it.
NAME_COLUMN_MARGIN = 8

RESERVED_NAMES = ['region0']

# The two halves of the region name rule that "IdentifierEdit" enforces, used to bring a name
# borrowed from a cell zone in line with it.
INVALID_NAME_CHARS = re.compile(r'[^A-Za-z0-9_.]+')
NAME_FIRST_CHAR = re.compile(r'[A-Za-z]')
NAME_KEEPS_ANYTHING = re.compile(r'[A-Za-z0-9]')

class RegionHeader(QWidget):
    def __init__(self, name: str, phase: str):
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


class RegionColumn(QObject):
    removeClicked = Signal(int)

    # "index" is both the position in the dialog's column list and the grid column the widgets
    # are laid out in. Removed columns are only hidden, never dropped, so it stays valid.
    def __init__(self, index, name: str, phase: str, cellZoneCount):
        super().__init__()

        self._index = index
        self._header = RegionHeader(name, phase)
        self._radios = [QRadioButton() for _ in range(cellZoneCount)]
        self._removeButton = FlatPushButton(removeIcon, '')
        self._hidden = False

        self._removeButton.clicked.connect(lambda: self.removeClicked.emit(self._index))

    def header(self):
        return self._header

    def radio(self, czindex):
        return self._radios[czindex]

    def removeButton(self):
        return self._removeButton

    def setChecked(self, czindex, checked: bool):
        self._radios[czindex].setChecked(checked)

    def isChecked(self, czindex):
        return self._radios[czindex].isChecked()

    def name(self):
        return None if self._hidden else self._header.name()

    def phase(self):
        return self._header.phase()

    def hide(self):
        self._header.hide()
        self._removeButton.hide()
        for radio in self._radios:
            radio.hide()

        self._hidden = True

    def isHidden(self):
        return self._hidden


def toLinedWidget(widget, alignment=Qt.AlignmentFlag.AlignLeft):
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)

    linedWidget = QWidget()
    layout = QGridLayout(linedWidget)
    layout.setContentsMargins(0, 6, 0, 0)
    layout.addWidget(widget, 0, 0, alignment)
    layout.addWidget(line, 1, 0)

    return linedWidget


class FluentRegionsDialog(QDialog):
    def __init__(self, parent, cellZones):
        super().__init__(parent)
        self._ui = Ui_FlluentRegionsDialog()
        self._ui.setupUi(self)

        # Cell zones are indexed from 0 here and laid out at "CELL_ZONE_START_ROW + index".
        self._cellZones = list(cellZones.items())
        # One group per cell zone makes that cell zone's radios mutually exclusive across the
        # region columns, so it can belong to only one region.
        self._buttonGroups = [QButtonGroup() for _ in self._cellZones]
        self._removeButtonRow = CELL_ZONE_START_ROW + len(self._cellZones)
        self._columns: list[RegionColumn] = []

        # The table is split into four areas that scroll together. "bodyGrid" holds the radio
        # buttons and owns the scrollbars; "headerGrid" (region names/phases) follows it
        # horizontally only, "nameGrid" (cell zone names) follows it vertically only, and the
        # corner stays put. Column widths and row heights are kept uniform across the grids so
        # the frozen header and name column stay aligned with the data.
        self._headerGrid: QGridLayout = self._ui.headerGrid
        self._nameGrid: QGridLayout = self._ui.nameGrid
        self._bodyGrid: QGridLayout = self._ui.bodyGrid

        self._columnWidth = RegionHeader('region', 'fluid').sizeHint().width()
        self._rowHeight = max(toLinedWidget(QLabel('Cell Zone')).sizeHint().height(),
                              toLinedWidget(QRadioButton(), Qt.AlignmentFlag.AlignCenter).sizeHint().height())

        self._connectSignalsSlots()

        fluidCellZones = []
        solidCellZones = []

        nameColumnWidth = 0
        for i, (czname, phase) in enumerate(self._cellZones):
            row = CELL_ZONE_START_ROW + i
            self._nameGrid.addWidget(toLinedWidget(QLabel(czname)), row, COLUMN_HEADER_ROW)
            nameColumnWidth = max(nameColumnWidth, QLabel(czname).sizeHint().width())
            self._nameGrid.setRowMinimumHeight(row, self._rowHeight)
            self._bodyGrid.setRowMinimumHeight(row, self._rowHeight)
            (solidCellZones if phase == 'solid' else fluidCellZones).append(i)

        # The body has an extra row of remove buttons. Reserve the same height in the name
        # column so both areas scroll over an identical height.
        removeRowHeight = FlatPushButton(removeIcon, '').sizeHint().height()
        self._nameGrid.addWidget(QWidget(), self._removeButtonRow, COLUMN_HEADER_ROW)
        self._nameGrid.setRowMinimumHeight(self._removeButtonRow, removeRowHeight)
        self._bodyGrid.setRowMinimumHeight(self._removeButtonRow, removeRowHeight)

        self._ui.nameScroll.setFixedWidth(nameColumnWidth + NAME_COLUMN_MARGIN)

        # Let a trailing empty row absorb any height left over when the dialog is taller than
        # the table, so the rows themselves keep the exact heights set above.
        self._nameGrid.setRowStretch(self._removeButtonRow + 1, 1)
        self._bodyGrid.setRowStretch(self._removeButtonRow + 1, 1)

        # The fluid cell zones share a single region, while every solid cell zone starts out in
        # a region of its own that is named after the cell zone. The names are worked out before
        # any column exists, so that each one can steer clear of the others.
        solidNames = []
        for i in solidCellZones:
            solidNames.append(self._regionNameFor(self._cellZones[i][0], solidNames))

        fluidColumn = self._addColumn('fluid', self._uniqueRegionName(solidNames))
        for i in fluidCellZones:
            fluidColumn.setChecked(i, True)

        for i, rname in zip(solidCellZones, solidNames):
            self._addColumn('solid', rname).setChecked(i, True)

        # Keep the first column unremovable, so a column being removed always has a visible one
        # before it to take over its cell zones.
        self._columns[0].removeButton().hide()

        # The body reserves the width of its vertical scrollbar and the height of its
        # horizontal one. Reserve the same amounts beside the header and under the name column
        # so all four areas keep identical viewports, then mirror the body's scrolling.
        self._ui.headerScroll.setFixedHeight(self._ui.headerArea.sizeHint().height())
        self._ui.headerSpacer.setFixedWidth(self._ui.bodyScroll.verticalScrollBar().sizeHint().width())

        self._ui.bodyScroll.horizontalScrollBar().valueChanged.connect(
            self._ui.headerScroll.horizontalScrollBar().setValue)
        self._ui.bodyScroll.verticalScrollBar().valueChanged.connect(
            self._ui.nameScroll.verticalScrollBar().setValue)
        self._ui.bodyScroll.horizontalScrollBar().rangeChanged.connect(self._syncNameSpacer)
        self._syncNameSpacer()

    def _connectSignalsSlots(self):
        self._ui.addRegion.clicked.connect(self._addRegion)
        self._ui.ok.clicked.connect(self._accept)

    def _addRegion(self):
        self._addColumn()

        # The scroll range only widens once the new column has been laid out, so bring the
        # region into view on the next range change rather than right away.
        self._ui.bodyScroll.horizontalScrollBar().rangeChanged.connect(
            self._revealNewRegion, Qt.ConnectionType.SingleShotConnection)

    def _revealNewRegion(self, _minimum, maximum):
        self._ui.bodyScroll.horizontalScrollBar().setValue(maximum)

    def _syncNameSpacer(self):
        # The body only gives up height to its horizontal scrollbar while that bar is shown,
        # so the name column reserves that height only then.
        hScrollBar = self._ui.bodyScroll.horizontalScrollBar()
        self._ui.nameSpacer.setFixedHeight(hScrollBar.sizeHint().height() if hScrollBar.maximum() > 0 else 0)

    def _nameTaken(self, name, taken):
        if name in taken or name in RESERVED_NAMES:
            return True

        for col in self._columns:
            if name == col.name():
                return True

        return False

    def _uniqueRegionName(self, taken=()):
        seq = 1
        name = 'region1'
        while self._nameTaken(name, taken):
            seq += 1
            name = f'region{seq}'

        return name

    # Cell zone names come from the Fluent mesh and are not bound by the region name rules, so
    # a name borrowed from one has to be brought in line with "IdentifierEdit" first.
    def _regionNameFor(self, czname, taken=()):
        name = INVALID_NAME_CHARS.sub('_', czname).strip('_.')
        if not NAME_FIRST_CHAR.match(name):
            # A name written entirely in non-ASCII, say, leaves nothing worth keeping, so fall
            # back to a generated name rather than a row of underscores.
            if not NAME_KEEPS_ANYTHING.search(name):
                return self._uniqueRegionName(taken)

            name = f'region_{name}'

        if not self._nameTaken(name, taken):
            return name

        seq = 2
        while self._nameTaken(f'{name}_{seq}', taken):
            seq += 1

        return f'{name}_{seq}'

    def _addColumn(self, phase='fluid', name=None):
        if name is None:
            name = self._uniqueRegionName()

        index = len(self._columns)
        column = RegionColumn(index, name, phase, len(self._cellZones))
        column.removeClicked.connect(self._removeColumn)
        self._columns.append(column)

        self._headerGrid.addWidget(column.header(), HEADER_ROW, index)
        for i in range(len(self._cellZones)):
            radio = column.radio(i)
            self._bodyGrid.addWidget(toLinedWidget(radio, Qt.AlignmentFlag.AlignCenter),
                                     CELL_ZONE_START_ROW + i, index)
            self._buttonGroups[i].addButton(radio)

        self._bodyGrid.addWidget(column.removeButton(), self._removeButtonRow, index,
                                 Qt.AlignmentFlag.AlignCenter)

        self._headerGrid.setColumnMinimumWidth(index, self._columnWidth)
        self._bodyGrid.setColumnMinimumWidth(index, self._columnWidth)

        # Region name editors stretch but radio buttons do not, so without this the two grids
        # would share leftover width differently. Park the stretch on the trailing empty
        # column instead, keeping every region column at exactly "_columnWidth".
        for grid in (self._headerGrid, self._bodyGrid):
            grid.setColumnStretch(index, 0)
            grid.setColumnStretch(index + 1, 1)

        return column

    def _removeColumn(self, index):
        target = self._columns[index]

        # Collapse the removed column so it leaves no empty gap between the remaining ones.
        self._headerGrid.setColumnMinimumWidth(index, 0)
        self._bodyGrid.setColumnMinimumWidth(index, 0)

        substitute = next(c for c in reversed(self._columns[:index]) if not c.isHidden())
        for i in range(len(self._cellZones)):
            if target.isChecked(i):
                substitute.setChecked(i, True)

        target.hide()

    @qasync.asyncSlot()
    async def _accept(self):
        cellZones = {czname: 'fluid' for czname, _ in self._cellZones}
        regions = {}

        for col in self._columns:
            if col.isHidden():
                continue

            rname = col.name()
            if rname in RESERVED_NAMES:
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('{} is an unavailable region name').format(rname))
                return

            if rname in regions:
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('{} is used as a region name more than once').format(rname))
                return

            regionCellZones = []
            for i, (czname, _) in enumerate(self._cellZones):
                if col.isChecked(i):
                    regionCellZones.append(czname)
                    cellZones[czname] = col.phase()

            if regionCellZones:
                regions[rname] = {
                    'cellZones': regionCellZones,
                    'type': col.phase()
                }

        CellZonesToRegions().setCellZoneRegions(cellZones, regions).write()

        self.accept()



