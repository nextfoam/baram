#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import sys
import typing

import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QWidget, QVBoxLayout
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem

SIDE_MARGIN = 0.05  # 5% margin between line end and right axis
WIDTH_RATIO = 0.5 / (0.5 + SIDE_MARGIN)     # Ratio of the chart width excluding margins
LEFT_RATIO = 1 - SIDE_MARGIN


class ChartWidget(QWidget):
    def __init__(self, width=10):
        super().__init__()

        self._data = None

        self._chart = None
        self._lines: typing.Dict[str, PlotDataItem] = {}

        self._logScale = False
        self._width = width

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.clear()

    def setTitle(self, title):
        self._chart.setTitle(title) # color="b", size="20pt"

    def logScaleOn(self):
        self._logScale = True
        self._chart.setLogMode(False, True)

    def fitChart(self):
        self._chart.autoRange()

    def appendData(self, data: pd.DataFrame):
        if self._data is None:
            self._data = data
        else:
            self._data = pd.concat([self._data[self._data.index < data.first_valid_index()], data])

        # d = self._data.reset_index()  # "Time" is back to a column to serve as X value in numpy transpose below
        times = self._data.index.to_numpy()

        for c in self._data.columns.values.tolist():
            if c not in self._lines:
                self._lines[c] = self._chart.plot(times, self._data[c].to_numpy(), name=c, pen={'color': '#1f77b4', 'width': 2})
            else:
                self._lines[c].setData(times, self._data[c].to_numpy())

        range = self._chart.viewRect()
        self._adjustRange(self._chart, [[range.left(), range.right()], [range.bottom(), range.top()]])

    def clear(self):
        if self._chart:
            self._chart.sigRangeChanged.disconnect(self._adjustRange)
            self.layout().removeWidget(self._chart)
            self._chart.deleteLater()

        self._data = None
        self._lines = {}

        self._chart = pg.PlotWidget(background='w')

        self._chart.setLogMode(False, self._logScale)
        self._chart.setXRange(0, self._width, padding=SIDE_MARGIN)
        self._chart.sigRangeChanged.connect(self._adjustRange)

        plotItem: pg.PlotItem = self._chart.getPlotItem()

        plotItem.setMouseEnabled(True, False)
        plotItem.getViewBox().setBorder('k')
        plotItem.showGrid(True, True)

        legend = pg.LegendItem(offset=(-10, 10+30), pen='lightGray', brush='w')  # Chart Title has a height of 30
        legend.setZValue(1)  # Raise LegendItem over Grid (Z-Value of Grid is 0.5)
        legend.setParentItem(plotItem)

        plotItem.legend = legend

        self.layout().addWidget(self._chart)

    def _adjustedYRange(self, minX: float, maxX: float):
        d = self._data[(self._data.index >= minX * LEFT_RATIO) & (self._data.index <= maxX)]

        minY = d.min().min()
        maxY = d.max().max()

        if self._logScale:
            # value cannot be "0" or close to "0" in log scale chart
            minY = max(minY, sys.float_info.min)
            maxY = max(maxY, sys.float_info.min)

            minY = minY / 10  # margin in log scale

            if maxY < 0.1:
                maxY = maxY * 10  # margin in log scale
            else:
                maxY = 1

            return [math.log10(minY), math.log10(maxY)]
        else:
            margin = (maxY - minY) * SIDE_MARGIN
            if margin < sys.float_info.epsilon:
                if minY == 0:
                    return [-1, 1]
                else:
                    a = abs(minY)
                    g = math.floor(math.log10(a))
                    p = float(pow(10, g))
                    v = math.floor(a / p)

                    bottom = v * p
                    top = bottom + p
                    if minY - bottom < sys.float_info.epsilon:
                        bottom = bottom - p
                    if minY < 0:
                        bottom, top = -top, -bottom

                    return [bottom, top]
            else:
                return [minY - margin, maxY + margin]

    def _adjustRange(self, widget, range):
        if self._data is None:
            return

        xRange, yRange = range
        minX, maxX = xRange
        width = (maxX - minX) * WIDTH_RATIO

        maxTime = float(self._data.last_valid_index())
        if minX < 0 and maxX >= maxTime:
            return

        if maxTime < width:
            minX = 0
            maxX = width
        else:
            minX = maxTime - width
            maxX = maxTime

        with QSignalBlocker(self._chart):
            yRange = self._adjustedYRange(minX, maxX)
            self._chart.setRange(xRange=[minX, maxX], yRange=yRange, padding=SIDE_MARGIN)
