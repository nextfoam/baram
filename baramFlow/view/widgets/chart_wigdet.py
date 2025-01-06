#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import sys
import typing

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QWheelEvent, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout
from pyqtgraph import AxisItem
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem

SIDE_MARGIN = 0.05  # 5% margin between line end and right axis

COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


class MajorOnlyAxisItem(AxisItem):
    def tickValues(self, minVal, maxVal, size):
        tickLevels = super().tickValues(minVal, maxVal, size)
        return tickLevels[:1]  # Leave major tick only


class WheelPlotWidget(pg.PlotWidget):
    onScroll = Signal(QWheelEvent)

    def wheelEvent(self, ev: QWheelEvent):
        self.onScroll.emit(ev)
        ev.accept()


class ChartWidget(QWidget):
    def __init__(self, width=10):
        super().__init__()

        self._data = None

        self._chart = None
        self._title = None
        self._lines: typing.Dict[str, PlotDataItem] = {}

        self._logScale = False
        self._width = width

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.clear()

    def setTitle(self, title):
        self._chart.setTitle(title, color='#5f5f5f', size='12pt')
        self._title = title

    def logScaleOn(self):
        self._logScale = True
        self._chart.setLogMode(False, True)

    def fitChart(self):
        if self._data is None:
            return

        minX = float(self._data.first_valid_index())
        maxX = float(self._data.last_valid_index())

        if maxX <= minX:
            maxX = minX + 1

        dataWidth = maxX - minX
        margin = dataWidth * SIDE_MARGIN / (1 - 2 * SIDE_MARGIN)

        self._chart.setXRange(minX-margin, maxX+margin)
        # To update Y range
        self._updateChart(1.0)

    def dataAppended(self, data: pd.DataFrame):
        if self._data is None:
            self._data = data
        else:
            self._data = pd.concat([self._data[self._data.index < data.first_valid_index()], data])

        self._drawLines()

    def _drawLines(self):
        times = self._data.index.to_numpy()

        for c in self._data.columns.values.tolist():
            if c not in self._lines:
                self._lines[c] = self._chart.plot(
                    times, self._data[c].to_numpy(), name=c, pen={'color': COLORS[len(self._lines) % 10], 'width': 2})
            else:
                self._lines[c].setData(times, self._data[c].to_numpy())

        self._updateChart(1.0)

    def dataUpdated(self, data: pd.DataFrame):
        self._data = data
        self._drawLines()

    def onScroll(self, ev: QWheelEvent):
        angle = ev.angleDelta().y() / 8.0
        scale = np.power(1.05, -angle/15)  # 15 degree is usually one step on mouse wheel

        self._updateChart(scale)

    def _updateChart(self, scale: float):
        if self._data is None:
            return

        data = self._data

        minTime = float(data.first_valid_index())
        maxTime = float(data.last_valid_index())

        dataWidth = maxTime - minTime

        # chartWidth is effective width for lines excluding side margins
        xRange, _ = self._chart.viewRange()
        margin = (xRange[1] - xRange[0]) * SIDE_MARGIN
        chartWidth = ((xRange[1] - xRange[0]) - 2 * margin)

        margin *= scale
        chartWidth *= scale

        if dataWidth < chartWidth:
            minX = minTime
            maxX = minX + chartWidth
        else:
            maxX = maxTime
            minX = maxTime - chartWidth

        left = minX - margin
        right = maxX + margin

        d = data[(data.index >= minX) & (data.index <= maxX)]
        minY = d.min().min()
        maxY = d.max().max()

        if self._logScale:
            # value cannot be "0" or close to "0" in log scale chart
            minY = max(minY, sys.float_info.min)
            maxY = max(maxY, sys.float_info.min)

            # 10x margin in log scale
            bottom = minY / 10
            top    = maxY * 10

            bottom = math.log10(bottom)
            top    = math.log10(top)
        else:
            margin = (maxY - minY) * SIDE_MARGIN
            if margin < sys.float_info.epsilon:  # minY and maxY are almost same
                if minY == 0:
                    margin = 1
                else:
                    exponent = math.floor(math.log10(abs(minY)))
                    margin = 10**exponent

            bottom = minY - margin
            top = maxY + margin

        self._chart.setRange(xRange=[left, right], yRange=[bottom, top])

    def clear(self):
        if self._chart:
            self._chart.onScroll.disconnect(self.onScroll)
            self.layout().removeWidget(self._chart)
            self._chart.deleteLater()

        self._data = None
        self._lines = {}

        self._chart = WheelPlotWidget(enableMenu=False, background='w')

        plotItem: pg.PlotItem = self._chart.getPlotItem()

        plotItem.setAxisItems({
            'left': MajorOnlyAxisItem('left', textPen='#5f5f5f', tickPen={'style': Qt.PenStyle.DashLine}),
            'bottom': MajorOnlyAxisItem('bottom', textPen='#5f5f5f', tickPen={'style': Qt.PenStyle.DashLine})
        })
        font = QFont()
        font.setPointSize(10)
        plotItem.getAxis('left').setTickFont(font)
        plotItem.getAxis('bottom').setTickFont(font)

        plotItem.setMouseEnabled(False, False)
        plotItem.setDefaultPadding(0)  # Padding is handled manually to set it asymmetrically
        plotItem.getViewBox().setBorder('k')
        plotItem.showGrid(True, True)
        plotItem.hideButtons()

        legend = pg.LegendItem(offset=(-10, 10+30), horSpacing=5, labelTextColor='#5f5f5f', labelTextSize='10pt', pen='lightGray', brush='w')  # Chart Title has a height of 30
        legend.setZValue(1)  # Raise LegendItem over Grid (Z-Value of Grid is 0.5)
        legend.setParentItem(plotItem)

        plotItem.legend = legend

        self._chart.setTitle(self._title, color='#5f5f5f', size='12pt')
        self._chart.setLogMode(False, self._logScale)
        self._chart.setXRange(0, self._width)
        self._chart.onScroll.connect(self.onScroll)

        self.layout().addWidget(self._chart)

