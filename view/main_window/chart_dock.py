#!/usr/bin/env python
# -*- coding: utf-8 -*-
import typing
from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

import numpy as np

from matplotlib import ticker
from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from openfoam.solver_info_manager import SolverInfoManager
from openfoam.file_system import FileSystem
from .tabified_dock import TabifiedDock
from coredb import coredb
from coredb.general_db import GeneralDB
from coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from coredb.project import Project, SolverStatus

SIDE_MARGIN = 0.05  # 5% margin on left and right


class ChartDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._main_window = parent

        self._data = None

        self._lines: typing.Dict[str, Line2D] = {}

        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._widget = QWidget()
        self.setWidget(self._widget)

        layout = QtWidgets.QVBoxLayout(self._widget)

        self._canvas = FigureCanvas(Figure(figsize=(5, 3)))
        self._canvas.mpl_connect('scroll_event', self.onScroll)

        layout.addWidget(self._canvas)

        self._axes = self._canvas.figure.subplots()

        self._clear()

        self.solverInfoManager = SolverInfoManager()
        self.solverInfoManager.residualsUpdated.connect(self.updated)

        self._project = Project.instance()
        self._project.projectOpened.connect(self._projectOpened)
        self._project.projectClosed.connect(self._projectClosed)
        self._project.solverStatusChanged.connect(self._solverStatusChanged)

        self._translate()

    def startDrawing(self):
        self.solverInfoManager.startCollecting(Path(FileSystem.caseRoot()).resolve(), coredb.CoreDB().getRegions())

    def stopDrawing(self):
        self.solverInfoManager.stopCollecting()

    def _projectOpened(self):
        if self._project.isSolverRunning() or self._project.hasSolved():
            self.startDrawing()

    def _projectClosed(self):
        self.stopDrawing()

    def _solverStatusChanged(self, status):
        if status == SolverStatus.NONE:
            self._clear()
        elif status == SolverStatus.RUNNING:
            self.startDrawing()
        else:
            self.stopDrawing()

    def updated(self, data: pd.DataFrame):
        self._data = data

        d = data.reset_index()  # "Time" is back to a column to serve as X value in numpy transpose below

        for c in data.columns.values.tolist():
            if c not in self._lines:
                self._lines[c], = self._axes.plot('Time', c, '', label=c, data=d)
                self._lines[c].set_linewidth(0.8)
            else:
                self._lines[c].set_data(d[['Time', c]].to_numpy().transpose())

        legend = self._axes.legend()
        for h in legend.legendHandles:
            h.set_linewidth(1.6)

        self._updateChart(1.0)

    def onScroll(self, event):
        scale = np.power(1.05, -event.step)
        self._updateChart(scale)

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

        self._translate()

    def _translate(self):
        self.setWindowTitle(self.tr("Residuals"))

    def _adjustYRange(self, minX: float, maxX: float):
        data = self._data

        d = data[(data.index >= minX) & (data.index <= maxX)]
        minY = d[d > 0].min().min()  # Residual value of "0" has been shown once
        maxY = d.max().max()

        minY = minY / 10  # margin in log scale

        if maxY < 0.1:
            maxY = maxY * 10  # margin in log scale
        else:
            maxY = 1

        self._axes.set_ylim([minY, maxY])

    def _clear(self):
        self._axes.cla()

        self._data = None
        self._lines = {}

        self._axes.grid(alpha=0.6, linestyle='--')
        self._axes.xaxis.set_major_formatter(ticker.FuncFormatter(lambda num, _: '{:g}'.format(num)))
        self._axes.yaxis.set_major_formatter(ticker.FuncFormatter(lambda num, _: '{:g}'.format(num)))
        self._axes.set_yscale('log')

        if GeneralDB.isTimeTransient():
            timeSteppingMethod = coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeSteppingMethod')
            if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
                # 50 Residual points
                timeStep = float(coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeStepSize'))
                chartWidth = timeStep * 50
            else:
                # 10% of total case time
                endTime = float(coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/endTime'))
                chartWidth = endTime / 10
        else:
            # 50 Residual points
            chartWidth = 50

        margin = chartWidth * SIDE_MARGIN
        minX = -margin
        maxX = chartWidth + margin
        self._axes.set_xlim([minX, maxX])

        self._canvas.draw()
