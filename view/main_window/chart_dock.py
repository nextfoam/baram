#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import QVBoxLayout, QWidget, QTextBrowser
from PySide6.QtCore import Qt

import numpy as np
import random

from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.ticker as ticker

from openfoam.solver_info_manager import getSolverInfoManager
from openfoam.file_system import FileSystem
from .tabified_dock import TabifiedDock

END_MARGIN = 0.05  # 5% margin between line end and right axis

class ChartDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._data = None
        self._timeMax = None
        self._lines = {}

        self.setWindowTitle(self.tr("Chart"))
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._widget = QWidget()
        self.setWidget(self._widget)

        layout = QtWidgets.QVBoxLayout(self._widget)

        self._canvas = FigureCanvas(Figure(figsize=(5, 3)))
        self._canvas.mpl_connect('scroll_event', self.onScroll)

        layout.addWidget(self._canvas)

        self._axes = self._canvas.figure.subplots()
        self._axes.grid(alpha=0.6, linestyle='--')
        self._axes.xaxis.set_major_formatter(ticker.FuncFormatter(lambda num, _: '{:g}'.format(num)))
        self._axes.yaxis.set_major_formatter(ticker.FuncFormatter(lambda num, _: '{:g}'.format(num)))
        self._axes.set_yscale('log')

        self.solverInfoManager = getSolverInfoManager(Path(FileSystem.caseRoot()).resolve())

        self.solverInfoManager.residualsUpdated.connect(self.updated)

    def startDrawing(self):
        self.solverInfoManager.startCollecting()

    def stopDrawing(self):
        self.solverInfoManager.stopCollecting()

    def updated(self, data):
        self._data = data

        d = data.reset_index()  # "Time" is back to a column to serve as X value in numpy transpose below

        columns = list(filter(lambda x: x.endswith('_initial'),
                              data.columns.values.tolist()))

        for c in columns:
            if c not in self._lines:
                self._lines[c], = self._axes.plot('Time', c, '', label=c[:-8], data=d)
                arrStyleLine = ["-", "--", "-.", ":"]
                self._lines[c].set_linestyle(arrStyleLine[random.randrange(3)])
                self._lines[c].set_linewidth(0.8)
            else:
                self._lines[c].set_data(d[['Time', c]].to_numpy().transpose())

        timeMax = data.last_valid_index()

        if self._timeMax is not None and timeMax > self._timeMax:
            delta = timeMax - self._timeMax
        else:
            delta = 0

        self._timeMax = timeMax

        minX, maxX = self._axes.get_xlim()

        minX += delta

        # If maxX is too far from current time max, adjust maxX to guarantee the margin
        if (maxX - self._timeMax) / (maxX - minX) > END_MARGIN:
            maxX = (self._timeMax - minX*END_MARGIN) / (1 - END_MARGIN)
        else:
            maxX += delta

        self._axes.set_xlim([minX, maxX])

        self._adjustYRange(data, minX, maxX)

        self._axes.legend()

        self._canvas.draw()
        # self._canvas.draw_idle()

    def onScroll(self, event):
        if self._timeMax is None:
            return

        minX, maxX = self._axes.get_xlim()
        scale = np.power(1.05, -event.step)

        width = (maxX - minX) * scale
        maxX = self._timeMax + width * END_MARGIN
        minX = self._timeMax - width * (1 - END_MARGIN)

        self._axes.set_xlim([minX, maxX])

        self._adjustYRange(self._data, minX, maxX)

        self._canvas.draw()  # force re-draw the next time the GUI refreshes
        # self._canvas.draw_idle()

    def _adjustYRange(self, data: [pd.DataFrame], minX: float, maxX: float):
        minY = None
        maxY = None

        columns = list(filter(lambda x: x.endswith('_initial'),
                              data.columns.values.tolist()))
        d = data[(data.index >= minX) & (data.index <= maxX)][columns]

        if minY is None or minY > d.min().min():
            minY = d.min().min()
        if maxY is None or maxY < d.max().max():
            maxY = d.max().max()

        minY = minY / 10  # margin in log scale
        if maxY < 0.1:
            maxY = maxY * 10  # margin in log scale
        else:
            maxY = 1

        self._axes.set_ylim([minY, maxY])


