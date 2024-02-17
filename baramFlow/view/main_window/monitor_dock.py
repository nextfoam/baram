#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout
from PySide6.QtCore import Qt

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project, SolverStatus
from baramFlow.view.widgets.flow_layout import FlowLayout
from baramFlow.view.widgets.chart_wigdet import ChartWidget
from baramFlow.openfoam.post_processing.monitor import ForceMonitor, PointMonitor, SurfaceMonitor, VolumeMonitor, calculateMaxX
from .tabified_dock import TabifiedDock


class MonitorDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setupUi()

        self._main_window = parent
        self._project = Project.instance()
        self._monitors = {}
        self._deletedMonitors = None

        self._project.projectOpened.connect(self._projectOpened)
        self._project.projectClosed.connect(self._projectClosed)
        self._project.solverStatusChanged.connect(self._solverStatusChanged)

        self._translate()

    def _translate(self):
        self.setWindowTitle(self.tr("Monitor"))

    def _setupUi(self):
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._widget = QWidget()
        self._layout = QVBoxLayout(self._widget)
        self._scrollArea = QScrollArea(self._widget)
        self._scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scrollArea.setWidgetResizable(True)

        self._chartsWidget = QWidget()
        self._chartsLayout = FlowLayout(self._chartsWidget)

        self._scrollArea.setWidget(self._chartsWidget)
        self._layout.addWidget(self._scrollArea)
        self.setWidget(self._widget)

    def _projectOpened(self):
        self.clear()

        if app.solver.isRunning() or app.solver.isEnded():
            self._startMonitor()

    def _projectClosed(self):
        self._stopMonitor()
        self.clear()

    def _solverStatusChanged(self, status):
        if status == SolverStatus.NONE:
            self._deletedMonitors = self._monitors
            self.clear()
        elif status == SolverStatus.RUNNING:
            self._startMonitor()
        elif status == SolverStatus.ENDED:
            self._stopMonitor()

    def clear(self):
        self._quitMonitor()

        while item := self._chartsLayout.takeAt(0):
            item.widget().deleteLater()

        self._monitors = {}

    def _startMonitor(self):
        if self._monitors:
            for name in self._monitors:
                self._monitors[name].start()
        else:
            maxX = calculateMaxX()

            db = coredb.CoreDB()
            for name in db.getForceMonitors():
                self._addMonitor(
                    ForceMonitor(name, self._createChart(maxX), self._createChart(maxX), self._createChart(maxX)))
            for name in db.getPointMonitors():
                self._addMonitor(PointMonitor(name, self._createChart(maxX)))
            for name in db.getSurfaceMonitors():
                self._addMonitor(SurfaceMonitor(name, self._createChart(maxX)))
            for name in db.getVolumeMonitors():
                self._addMonitor(VolumeMonitor(name, self._createChart(maxX)))

    def _stopMonitor(self):
        if self._monitors:
            for name in self._monitors:
                self._monitors[name].stop()

    def _quitMonitor(self):
        if self._monitors:
            for name in self._monitors:
                self._monitors[name].quit()

    def _addMonitor(self, monitor):
        self._monitors[monitor.name] = monitor
        monitor.stopped.connect(self._removeMonitor)
        monitor.start()

    def _removeMonitor(self, name):
        if self._deletedMonitors:
            del self._deletedMonitors[name]

    def _createChart(self, maxX):
        chart = ChartWidget()
        self._chartsLayout.addWidget(chart)
        return chart


