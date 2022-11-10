#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

import numpy as np
import random

from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.ticker as ticker

from openfoam.solver_info_manager import SolverInfoManager
from openfoam.file_system import FileSystem
from .tabified_dock import TabifiedDock
from coredb import coredb
from coredb.general_db import GeneralDB
from coredb.run_calculation_db import RunCalculationDB
from coredb.project import Project, SolverStatus

END_MARGIN = 0.05  # 5% margin between line end and right axis


class ChartDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._main_window = parent

        self._data = None
        self._timeMax = None
        self._timeMin = None
        self._lines = {}

        self.setWindowTitle(self.tr("Residuals"))
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

        if GeneralDB.isTimeTransient():
            # 10% of total case time
            endTime = float(coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/endTime'))
            maxX = endTime / 10
        else:
            # 10% of total iteration count or iteration count if it is less than MIN_COUNT
            MIN_COUNT = 100
            count = int(coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/numberOfIterations'))
            if count < MIN_COUNT:
                maxX = count
            else:
                maxX = MIN_COUNT + count / 10

        self._axes.set_xlim([-(maxX * END_MARGIN), maxX])

        self.solverInfoManager = SolverInfoManager()
        self.solverInfoManager.residualsUpdated.connect(self.updated)

        self._project = Project.instance()
        self._project.solverStatusChanged.connect(self.solverStatusChanged)

        self._main_window.windowClosed.connect(self._mainWindowClosed)

    def startDrawing(self):
        self._timeMax = None
        self._timeMin = None
        self.solverInfoManager.startCollecting(
            Path(FileSystem.caseRoot()).resolve(),
            coredb.CoreDB().getRegions())

    def stopDrawing(self):
        self.solverInfoManager.stopCollecting()

    def solverStatusChanged(self, status):
        if status == SolverStatus.RUNNING:
            self.startDrawing()
        else:
            self.stopDrawing()

    def _mainWindowClosed(self, result):
        self.stopDrawing()

    def updated(self, data: pd.DataFrame):
        self._data = data

        d = data.reset_index()  # "Time" is back to a column to serve as X value in numpy transpose below

        columns = list(filter(lambda x: x.endswith('_initial'),
                              data.columns.values.tolist()))

        for c in columns:
            if c not in self._lines:
                self._lines[c], = self._axes.plot('Time', c, '', label=c[:-8], data=d)
                self._lines[c].set_linewidth(0.8)
            else:
                self._lines[c].set_data(d[['Time', c]].to_numpy().transpose())

        timeMax = float(data.last_valid_index())
        timeMin = float(data.first_valid_index())

        minX, maxX = self._axes.get_xlim()
        chartWidth = (maxX - minX)

        if self._timeMax is None:  # new drawing
            dataWidth = chartWidth * (1 - 2 * END_MARGIN)
            if (timeMax - timeMin) > dataWidth:
                maxX = timeMax + chartWidth * END_MARGIN
                minX = maxX - chartWidth
            else:
                minX = timeMin - END_MARGIN
                maxX = minX + chartWidth
        else:
            if timeMax + chartWidth * END_MARGIN < maxX:
                pass  # keep the range as is
            else:
                maxX = timeMax + chartWidth * END_MARGIN
                minX = maxX - chartWidth

        self._timeMax = timeMax
        self._timeMin = timeMin

        self._axes.set_xlim([minX, maxX])

        self._adjustYRange(data, minX, maxX)

        legend = self._axes.legend()
        for h in legend.legendHandles:
            h.set_linewidth(1.6)

        self._canvas.draw()
        # self._canvas.draw_idle()

    def onScroll(self, event):
        if self._timeMax is None:
            return

        minX, maxX = self._axes.get_xlim()
        width = maxX - minX

        # this margin will be kept without change
        margin = (maxX - self._timeMax) / width

        scale = np.power(1.05, -event.step)

        newWidth = width * scale

        if scale < 1:  # Zoom in
            # if self._timeMax + width * END_MARGIN >= maxX:
            if minX > self._timeMin or maxX <= self._timeMax + width * END_MARGIN:
                maxX = self._timeMax + newWidth * margin
                minX = self._timeMax - newWidth * (1 - margin)
            else:
                maxX = minX + newWidth
        else:  # Zoom out
            if minX >= self._timeMin:
                maxX = self._timeMax + newWidth * margin
                minX = self._timeMax - newWidth * (1 - margin)
            else:
                maxX = minX + newWidth

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

        minimum = d[d > 0].min().min()  # Residual value of "0" has been shown once
        if minY is None or minY > minimum:
            minY = minimum

        if maxY is None or maxY < d.max().max():
            maxY = d.max().max()

        minY = minY / 10  # margin in log scale
        if maxY < 0.1:
            maxY = maxY * 10  # margin in log scale
        else:
            maxY = 1

        self._axes.set_ylim([minY, maxY])


