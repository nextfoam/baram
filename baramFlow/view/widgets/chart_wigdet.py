#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import sys
import typing

from PySide6.QtWidgets import QWidget

import numpy as np
import pandas as pd
from matplotlib import ticker
from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas)
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.run_calculation_db import TimeSteppingMethod, RunCalculationDB

SIDE_MARGIN = 0.05  # 5% margin between line end and right axis


class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._data = None

        self._lines: typing.Dict[str, Line2D] = {}

        self._logScale = False
        self._initialMaxX = 10

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._canvas = FigureCanvas(Figure(figsize=(5, 3), layout='tight'))
        self._canvas.mpl_connect('scroll_event', self._onScroll)

        layout.addWidget(self._canvas)

        self._axes = self._canvas.figure.subplots()
        self.clear()

    def setTitle(self, title):
        self._axes.set_title(title)

    def logScaleOn(self):
        self._logScale = True
        self._axes.set_yscale('log')

    def setData(self, data):
        self._data = data
        self._updateChart(1.0)

    def fitChart(self):
        if self._data is None:
            return

        minX = float(self._data.first_valid_index())
        maxX = float(self._data.last_valid_index())

        dataWidth = maxX - minX
        if dataWidth == 0:
            return

        margin = dataWidth * SIDE_MARGIN / (1 - 2 * SIDE_MARGIN)

        self._axes.set_xlim([minX-margin, maxX+margin])
        self._adjustYRange(minX, maxX)

        self._canvas.draw()

    def appendData(self, data: pd.DataFrame):
        if self._data is None:
            self._data = data
        else:
            self._data = pd.concat([self._data[self._data.index < data.first_valid_index()], data])

        d = self._data.reset_index()  # "Time" is back to a column to serve as X value in numpy transpose below

        for c in self._data.columns.values.tolist():
            if c not in self._lines:
                self._lines[c], = self._axes.plot('Time', c, '', label=c, data=d)
                self._lines[c].set_linewidth(0.8)
            else:
                self._lines[c].set_data(d[['Time', c]].to_numpy().transpose())

        legend = self._axes.legend()
        for h in legend.legendHandles:
            h.set_linewidth(1.6)

        self._updateChart(1.0)

    def clear(self):
        self._axes.cla()

        self._data = None
        self._lines = {}

        self._axes.grid(alpha=0.6, linestyle='--')
        self._axes.xaxis.set_major_formatter(ticker.FuncFormatter(lambda num, _: '{:g}'.format(num)))
        self._axes.yaxis.set_major_formatter(ticker.FuncFormatter(lambda num, _: '{:g}'.format(num)))
        if self._logScale:
            self._axes.set_yscale('log')

        if GeneralDB.isTimeTransient():
            timeSteppingMethod = coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeSteppingMethod')
            if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
                # 50 Residual points
                timeStep = float(
                    coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeStepSize'))
                chartWidth = timeStep * 50
            else:
                # 10% of total case time
                endTime = float(
                    coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/endTime'))
                chartWidth = endTime / 10
        else:
            # 50 Residual points
            chartWidth = 50

        margin = chartWidth * SIDE_MARGIN
        minX = -margin
        maxX = chartWidth + margin
        self._axes.set_xlim([minX, maxX])

        self._canvas.draw()

    def _updateChart(self, scale: float):
        if self._data is None:
            return

        timeMin = float(self._data.first_valid_index())
        timeMax = float(self._data.last_valid_index())

        dataWidth = timeMax - timeMin

        # chartWidth is effective width for lines excluding side margins
        left, right = self._axes.get_xlim()
        margin = (right - left) * SIDE_MARGIN
        chartWidth = ((right - left) - 2 * margin)

        margin *= scale
        chartWidth *= scale

        if dataWidth < chartWidth:
            minX = timeMin
            maxX = minX + chartWidth
        else:
            maxX = timeMax
            minX = maxX - chartWidth

        self._axes.set_xlim([minX-margin, maxX+margin])

        self._adjustYRange(minX, maxX)

        self._canvas.draw()  # force re-draw the next time the GUI refreshes
        # self._canvas.draw_idle()

    def _onScroll(self, event):
        scale = np.power(1.05, -event.step)
        self._updateChart(scale)

    def _adjustYRange(self, minX: float, maxX: float):
        data = self._data

        d = data[(data.index >= minX) & (data.index <= maxX)]
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

            self._axes.set_ylim([minY, maxY])

        else:
            margin = (maxY - minY) * SIDE_MARGIN
            if margin < sys.float_info.epsilon:
                if minY == 0:
                    self._axes.set_ylim([-1, 1])
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

                    self._axes.set_ylim([bottom, top])
            else:
                self._axes.set_ylim([minY-margin, maxY+margin])
