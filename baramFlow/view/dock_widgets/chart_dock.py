#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import typing
from pathlib import Path

import numpy as np
import pandas as pd
import pyqtgraph as pg
import qasync
from PySide6.QtCore import QMargins, QCoreApplication, QEvent, Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6QtAds import CDockWidget
from pyqtgraph import AxisItem
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem

from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.project import Project, SolverStatus
from baramFlow.coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver_info_manager import SolverInfoManager

SIDE_MARGIN = 0.05  # 5% margin on left and right

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

    def updated(self, data: pd.DataFrame):
        self._data = data

        times = data.index.to_numpy()

        for c in data.columns.values.tolist():
            if c not in self._lines:
                self._lines[c] = self._chart.plot(
                    times, data[c].to_numpy(), name=c, pen={'color': COLORS[len(self._lines) % 10], 'width': 2})
            else:
                self._lines[c].setData(times, data[c].to_numpy())

        self._updateChart(1.0)

    def onScroll(self, ev: QWheelEvent):
        angle = ev.angleDelta().y() / 8.0
        scale = np.power(1.05, -angle/15)  # 15 degree is usually one step on mouse wheel

        self._updateChart(scale)

    def _updateChart(self, scale: float):
        if self._data is None:
            return

        data = self._data

        timeMin = float(data.first_valid_index())
        timeMax = float(data.last_valid_index())

        dataWidth = timeMax - timeMin

        # chartWidth is effective width for lines excluding side margins
        xRange, _ = self._chart.viewRange()
        margin = (xRange[1] - xRange[0]) * SIDE_MARGIN
        chartWidth = ((xRange[1] - xRange[0]) - 2 * margin)

        margin *= scale
        chartWidth *= scale

        if dataWidth < chartWidth:
            minX = timeMin
            maxX = minX + chartWidth
        else:
            maxX = timeMax
            minX = maxX - chartWidth

        left = minX - margin
        right = maxX + margin

        d = data[(data.index >= minX) & (data.index <= maxX)]
        minY = d[d > 0].min().min()  # Residual value of "0" has been shown once
        maxY = d.max().max()

        # 10x margin in log scale
        bottom = minY / 10
        top    = maxY * 10

        bottom = math.log10(bottom)
        top    = math.log10(top)

        self._chart.setRange(xRange=[left, right], yRange=[bottom, top])

    def _clear(self):
        if self._chart:
            self._chart.onScroll.disconnect(self.onScroll)
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

        self._chart = WheelPlotWidget(enableMenu=False, background='w')

        plotItem: pg.PlotItem = self._chart.getPlotItem()
        plotItem.setAxisItems({
            'left': MajorOnlyAxisItem('left', tickPen={'style': Qt.PenStyle.DashLine}),
            'bottom': MajorOnlyAxisItem('bottom', tickPen={'style': Qt.PenStyle.DashLine})
        })

        plotItem.setMouseEnabled(False, False)
        plotItem.setDefaultPadding(0)  # Padding is handled manually to set it asymmetrically
        plotItem.getViewBox().setBorder('k')
        plotItem.showGrid(True, True)
        plotItem.hideButtons()

        legend = pg.LegendItem(offset=(-10, 10), pen='lightGray', brush='w')
        legend.setZValue(1)  # Raise LegendItem over Grid (Z-Value of Grid is 0.5)
        legend.setParentItem(plotItem)

        plotItem.legend = legend

        self._chart.setLogMode(False, True)
        self._chart.setXRange(0, self._width)
        self._chart.onScroll.connect(self.onScroll)

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
