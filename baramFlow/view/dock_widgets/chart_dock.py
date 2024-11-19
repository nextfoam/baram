#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import typing
from pathlib import Path

import pandas as pd
import pyqtgraph as pg
import qasync
from PySide6.QtCore import QMargins, QCoreApplication, QEvent, QSignalBlocker
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6QtAds import CDockWidget
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem

from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.project import Project, SolverStatus
from baramFlow.coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver_info_manager import SolverInfoManager

SIDE_MARGIN = 0.05  # 5% margin on left and right
WIDTH_RATIO = 0.5 / (0.5 + SIDE_MARGIN)     # Ratio of the chart width excluding margins
LEFT_RATIO = 1 - SIDE_MARGIN


COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


class ChartView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._data = None

        self._chart = None
        self._lines: typing.Dict[str, PlotDataItem] = {}

        self._solverInfoManager = SolverInfoManager()
        self._project = Project.instance()

        self._width = 10

        layout = QVBoxLayout(self)
        layout.setContentsMargins(QMargins(80, 80, 80, 80))

        self._clear()

        self._solverInfoManager.residualsUpdated.connect(self.updated)
        self._solverInfoManager.flushed.connect(self.fitChart)

        self._project.projectClosed.connect(self._projectClosed)
        self._project.solverStatusChanged.connect(self._solverStatusChanged)
        CaseManager().caseLoaded.connect(self._caseLoaded)
        CaseManager().caseCleared.connect(self._caseCleared)

    def startDrawing(self):
        self._solverInfoManager.startCollecting(Path(FileSystem.caseRoot()).resolve(), coredb.CoreDB().getRegions())

    def stopDrawing(self):
        self._solverInfoManager.stopCollecting()

    @qasync.asyncSlot()
    async def _caseLoaded(self):
        self._clear()
        if CaseManager().isRunning() or CaseManager().isEnded():
            self.startDrawing()

    def _caseCleared(self):
        self._clear()

    def _projectClosed(self):
        self.stopDrawing()

    @qasync.asyncSlot()
    async def _solverStatusChanged(self, status, name, liveStatusChanged):
        if status == SolverStatus.NONE:
            self._clear()
        elif status == SolverStatus.RUNNING:
            self.startDrawing()
        else:
            self.stopDrawing()

    def fitChart(self):
        self._chart.autoRange()

    def updated(self, data: pd.DataFrame):
        self._data = data

        # d = data.reset_index()  # "Time" is back to a column to serve as X value in numpy transpose below
        times = data.index.to_numpy()

        for c in data.columns.values.tolist():
            if c not in self._lines:
                self._lines[c] = self._chart.plot(
                    times, data[c].to_numpy(), name=c, pen=COLORS[len(self._lines) % 10])
            else:
                self._lines[c].setData(times, data[c].to_numpy())

        range = self._chart.viewRect()
        self._adjustRange(self._chart, [[range.left(), range.right()], [range.bottom(), range.top()]])

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

        d = self._data[(self._data.index >= minX * LEFT_RATIO) & (self._data.index <= maxX)]
        minY = d[d > 0].min().min()  # Residual value of "0" has been shown once
        maxY = d.max().max()

        yRange = None if d.empty else [math.log10(minY / 10), math.log10(maxY * 10)]   # margin in log scalse

        with QSignalBlocker(self._chart):
            self._chart.setRange(xRange=[minX, maxX], yRange=yRange, padding=SIDE_MARGIN)

    def _clear(self):
        if self._chart:
            self._chart.sigRangeChanged.disconnect(self._adjustRange)
            self.layout().removeWidget(self._chart)
            self._chart.deleteLater()

        self._data = None
        self._lines = {}
        #
        # self._axes.grid(alpha=0.6, linestyle='--')
        # self._axes.xaxis.set_major_formatter(ticker.FuncFormatter(lambda num, _: '{:g}'.format(num)))
        # self._axes.yaxis.set_major_formatter(ticker.FuncFormatter(lambda num, _: '{:g}'.format(num)))

        if GeneralDB.isTimeTransient():
            timeSteppingMethod = coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeSteppingMethod')
            if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
                # 50 Residual points
                timeStep = float(
                    coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeStepSize'))
                self._width = timeStep * 50
            else:
                # 10% of total case time
                endTime = float(
                    coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/endTime'))
                self._width = endTime / 10
        else:
            # 50 Residual points
            self._width = 50

        self._chart = pg.PlotWidget(background='w')
        self._chart.addLegend(offset=(-10, 10), pen='lightGray', brush='w')
        self._chart.setLogMode(False, True)
        self._chart.plotItem.setMouseEnabled(True, False)
        self._chart.plotItem.getViewBox().setBorder('k')
        self._chart.plotItem.showGrid(True, True)
        self._chart.setXRange(0, self._width, padding=SIDE_MARGIN)
        self._chart.sigRangeChanged.connect(self._adjustRange)

        self.layout().addWidget(self._chart)


class ChartDock(CDockWidget):
    def __init__(self):
        super().__init__(self._title())

        self._widget = ChartView()
        self.setWidget(self._widget)
        self.setStyleSheet('background-color: white')

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.setWindowTitle(self._title())

        super().changeEvent(event)

    def _title(self):
        return QCoreApplication.translate('ChartDock', 'Residuals')
