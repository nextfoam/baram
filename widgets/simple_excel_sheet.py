#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
from io import StringIO
import sys
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QRect, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QPainter, QPen, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QMenu,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
)


class RightAlignedDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Modify the option to add right padding
        option.rect.setRight(option.rect.right() - 8)  # 8px right padding
        super().paint(painter, option, index)


class SimpleExcelSheet(QTableWidget):
    MINIMUM_ROW_COUNT = 50
    ROWS_TO_ADD_ON_SCROLL = 5
    BUFFER_BLANK_ROWS = 3  # Keep at least this many blank rows at the end.

    SELECTION_BORDER_COLOR = QColor(33, 115, 70)
    SELECTION_BORDER_WIDTH = 2

    # Signal emitted when data changes
    dataUpdated = Signal()

    def setup(self, labels: list[str], data: Optional[list[list[float]]] = None, readOnly: bool = False):

        if data is None:
            data = []

        self._readOnly = readOnly

        if readOnly:
            self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        rowCount = max(len(data), self.MINIMUM_ROW_COUNT)
        colCount = len(labels)

        self.setRowCount(rowCount)
        self.setColumnCount(colCount)

        self.setHorizontalHeaderLabels(labels)

        # Set center alignment for row headers (vertical header)
        self.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        # Make columns fit the width of the parent widget
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Set Excel-like header styling
        self.setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                padding: 4px;
                font-weight: normal;
            }
            QHeaderView::section:horizontal {
                border-bottom: 2px solid #d0d0d0;
            }
            QHeaderView::section:vertical {
                border-right: 2px solid #d0d0d0;
            }
        """)

        for rowIndex, rowData in enumerate(data):
            for colIndex, cellData in enumerate(rowData):
                item = QTableWidgetItem(f'{cellData:g}')
                self.setItem(rowIndex, colIndex, item)

        self.verticalScrollBar().valueChanged.connect(self._handleValueChanged)
        self.verticalScrollBar().sliderReleased.connect(self._handleSliderReleased)

        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)

        self.selectionModel().selectionChanged.connect(self._onSelectionChanged)

        self.cellChanged.connect(self._validateCellData)
        self.itemChanged.connect(self._onItemChanged)

        self.copyShortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        self.copyShortcut.activated.connect(self._copyData)

        self.pasteShortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self.pasteShortcut.activated.connect(self._pasteData)

        self.deleteShortcut = QShortcut(QKeySequence.StandardKey.Delete, self)
        self.deleteShortcut.activated.connect(self._deleteData)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._showContextMenu)

        # Set custom delegate for right padding
        self.setItemDelegate(RightAlignedDelegate())

    def setItem(self, row, column, item):
        if item is not None:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        super().setItem(row, column, item)

    def _onItemChanged(self, item):
        if item is not None:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        QTimer.singleShot(10, self.dataUpdated.emit)

    def _onSelectionChanged(self):
        self.viewport().update()

    def getData(self) -> list[list[float]]:
        """Get the values in the table

        Get the values in the table

        Returns:
            the values in the table
            list of row data
        """
        # previousX = None
        stopCollection = False

        data: list[list[float]] = []
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if not item or not item.text().strip():  # check if cell is empty
                    stopCollection = True
                    break

            if stopCollection:
                break

            x = float(self.item(row, 0).text())
            #
            # if previousX is not None and x < previousX:
            #     break
            #
            # previousX = x

            rowData: list[float] = []
            for col in range(self.columnCount()):
                y = float(self.item(row, col).text())
                rowData.append(y)

            data.append(rowData)

        return data

    def isDataComplete(self, ascendingFirstColumn=False) -> bool:
        lastRow = -1
        # Iterate backwards from the last row to find the first one with content
        for row in range(self.rowCount() - 1, -1, -1):
            if not self._isRowBlank(row):
                lastRow = row
                break

        if lastRow < 0:
            return False

        maxValue = -sys.float_info.max
        for row in range(lastRow+1):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if not item or not item.text().strip():  # check if cell is empty
                    return False

                if col > 0:  # check only the first column values
                    continue

                value = float(item.text())
                if ascendingFirstColumn and value <= maxValue:
                    return False

                maxValue = value

        return True

    def paintEvent(self, event):
        super().paintEvent(event)

        selections = self.selectedRanges()
        if not selections:
            return

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self.SELECTION_BORDER_COLOR, self.SELECTION_BORDER_WIDTH)
        painter.setPen(pen)

        for selectionRange in selections:
            top    = selectionRange.topRow()
            left   = selectionRange.leftColumn()
            bottom = selectionRange.bottomRow()
            right  = selectionRange.rightColumn()

            width = 0
            for col in range(left, right + 1):
                width += self.columnWidth(col)

            height = 0
            for row in range(top, bottom + 1):
                height += self.rowHeight(row)

            # Adjust positioning to avoid grid lines and ensure uniform border thickness
            # Move inward by 1 pixel to avoid overlapping with grid lines

            x = self.columnViewportPosition(left)
            y = self.rowViewportPosition(top)

            gridOffset = 1
            selectionRectangle = QRect(
                x + gridOffset,
                y + gridOffset,
                width - 2 * gridOffset,
                height - 2 * gridOffset
            )

            viewportRectangle = self.viewport().rect()
            if selectionRectangle.intersects(viewportRectangle):  # check if visible
                painter.drawRect(selectionRectangle)

    def _handleValueChanged(self, value):
        scrollBar = self.verticalScrollBar()
        if value == scrollBar.maximum():
            self._addMoreRows()
        else:
            # Trim if the value is changed by wheel move
            # Value change caused by dragging is handled in "sliderReleased" event handler
            if not scrollBar.isSliderDown():
                self._trimExcessBlankRows()

    def _handleSliderReleased(self):
        self._trimExcessBlankRows()

    def _addMoreRows(self):
        count = self.rowCount()
        self.setRowCount(count + self.ROWS_TO_ADD_ON_SCROLL)

    def _isRowBlank(self, row_index):
        for col in range(self.columnCount()):
            item = self.item(row_index, col)
            if item and item.text().strip():
                return False # Found content, so row is not blank
        return True

    def _is_row_visible(self, row_index) -> bool:
        y = self.rowViewportPosition(row_index)
        rect = self.viewport().rect()
        if y >= rect.top() and y <= rect.bottom():
            return True
        else:
            return False

    def _trimExcessBlankRows(self):
        lastRow = -1
        # Iterate backwards from the last row to find the first one with content or visible
        for row in range(self.rowCount() - 1, -1, -1):
            if not self._isRowBlank(row) or self._is_row_visible(row):
                lastRow = row
                break

        if lastRow < 0:
            return

        desiredRows = lastRow + 1 + self.BUFFER_BLANK_ROWS
        newRowCount = max(self.MINIMUM_ROW_COUNT, desiredRows)

        if newRowCount < self.rowCount():
            self.setRowCount(newRowCount)

    def _validateCellData(self, row, column):
        item = self.item(row, column)
        if item is not None:
            text = item.text()
            if text:
                try:
                    float(text)
                except ValueError:
                    QTimer.singleShot(0, lambda: self.setItem(row, column, QTableWidgetItem("")))

    def _copyData(self):
        ranges = self.selectedRanges()
        if not ranges:
            return

        text = StringIO()
        writer = csv.writer(text, delimiter='\t')

        for selectedRange in ranges:
            for row in range(selectedRange.topRow(), selectedRange.bottomRow() + 1):
                data = []
                for col in range(selectedRange.leftColumn(), selectedRange.rightColumn() + 1):
                    item = self.item(row, col)
                    if item:
                        data.append(item.text())
                    else:
                        data.append('')
                writer.writerow(data)

        clipboard = QApplication.clipboard()
        clipboard.setText(text.getvalue())

    def _pasteData(self):
        if self._readOnly:
            return

        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if not text:
            return

        rowsToPaste = []
        for line in text.splitlines():
            rowsToPaste.append(line.split('\t'))

        if not rowsToPaste:
            return

        ranges = self.selectedRanges()
        if not ranges:
            return

        # Get the top-left corner of the selection
        topRow = min(selectedRange.topRow() for selectedRange in ranges)
        leftCol = min(selectedRange.leftColumn() for selectedRange in ranges)

        for rowIndex, rowData in enumerate(rowsToPaste):
            for colIndex, cellData in enumerate(rowData):
                row = topRow + rowIndex
                col = leftCol + colIndex

                # Check if the target cell is within the table bounds
                if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
                    try:
                        float(cellData)
                        item = QTableWidgetItem(cellData)
                        self.setItem(row, col, item)
                    except ValueError:
                        pass

    def _deleteData(self):
        if self._readOnly:
            return

        ranges = self.selectedRanges()
        if not ranges:
            return

        for selectedRange in ranges:
            for row in range(selectedRange.topRow(), selectedRange.bottomRow() + 1):
                for col in range(selectedRange.leftColumn(), selectedRange.rightColumn() + 1):
                    self.takeItem(row, col)

        QTimer.singleShot(10, self.dataUpdated.emit)

    def _showContextMenu(self, pos):
        menu = QMenu()  # Do not give parent so that stylesheet is not inherited

        action = menu.addAction("Copy")
        action.triggered.connect(self._copyData)

        if not self._readOnly:
            action = menu.addAction("Paste")
            action.triggered.connect(self._pasteData)

            menu.addSeparator()

            action = menu.addAction("Insert Row(s)")
            action.triggered.connect(self._insertRows)

            action = menu.addAction("Remove Row(s)")
            action.triggered.connect(self._removeRows)

        menu.exec(self.viewport().mapToGlobal(pos))

    def _insertRows(self):
        for row in self._selectedRows():
            self.insertRow(row)

    def _removeRows(self):
        for row in self._selectedRows():
            self.removeRow(row)

    def _selectedRows(self) -> list[int]:
        ranges = self.selectedRanges()
        if not ranges:
            return []

        rows = set()
        for selectedRange in ranges:
            for row in range(selectedRange.topRow(), selectedRange.bottomRow() + 1):
                rows.add(row)

        return sorted(rows, reverse=True)