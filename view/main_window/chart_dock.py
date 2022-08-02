#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import QVBoxLayout, QWidget, QTextBrowser
from PySide6.QtCore import Qt

import numpy as np

from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

from openfoam.file_system import FileSystem
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
        self._axes.set_yscale('log')

        self.solverInfoManager = getSolverInfoManager(Path(FileSystem.caseRoot()).resolve())

        self.solverInfoManager.updated.connect(self.updated)

    def startDrawing(self):
        self.solverInfoManager.startCollecting()

    def stopDrawing(self):
        self.solverInfoManager.stopCollecting()

    def updated(self, data):
        self._data = data

        timeMax = None
        for df in data:
            columns = list(filter(lambda x: x.endswith('_initial'),
                                  df.columns.values.tolist()))

            timeMax = df.last_valid_index()

            d = df.reset_index()  # "Time" is back to a column to serve as X value in numpy transpose below

            for c in columns:
                if c not in self._lines:
                    self._lines[c], = self._axes.plot('Time', c, '', label=c[:-8], data=d)
                else:
                    self._lines[c].set_data(d[['Time', c]].to_numpy().transpose())

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

    def _adjustYRange(self, data: [pd.DataFrame], minX: float, maxX: float):
        minY = None
        maxY = None
        for df in data:
            columns = list(filter(lambda x: x.endswith('_initial'),
                                  df.columns.values.tolist()))
            d = df[(df.index >= minX) & (df.index <= maxX)][columns]
            localMin = d.min().min()
            localMax = d.max().max()

            if minY is None or minY > localMin:
                minY = localMin
            if maxY is None or maxY < localMax:
                maxY = localMax

        minY = minY / 10  # margin in log scale
        if maxY < 0.1:
            maxY = maxY * 10  # margin in log scale
        else:
            maxY = 1

        self._axes.set_ylim([minY, maxY])


