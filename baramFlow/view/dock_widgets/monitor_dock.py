#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Qt, QCoreApplication, QEvent, QMargins
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout
from PySide6QtAds import CDockWidget

from baramFlow.case_manager import CaseManager
from baramFlow.coredb.project import Project, SolverStatus
from baramFlow.view.widgets.flow_layout import FlowLayout
from baramFlow.view.widgets.chart_wigdet import ChartWidget
from baramFlow.openfoam.post_processing.monitor import ForceMonitor, PointMonitor, SurfaceMonitor, VolumeMonitor
from baramFlow.openfoam.post_processing.monitor import calculateMaxX
from baramFlow.services.monitor.monitor_service import MonitorService


class MonitorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._setupUi()

        self._project = Project.instance()
        self._monitors = {}
        self._deletedMonitors = None

        self._connectSignalsSlots()

    def _setupUi(self):
        self._layout = QVBoxLayout(self)
        self._scrollArea = QScrollArea(self)
        self._scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scrollArea.setWidgetResizable(True)

        self._chartsWidget = QWidget()
        self._chartsLayout = FlowLayout(self._chartsWidget)

        self._scrollArea.setWidget(self._chartsWidget)
        self._layout.addWidget(self._scrollArea)

    def _connectSignalsSlots(self):
        self._project.projectClosed.connect(self._projectClosed)
        self._project.solverStatusChanged.connect(self._solverStatusChanged)
        CaseManager().caseLoaded.connect(self._caseLoaded)
        CaseManager().caseCleared.connect(self._clear)
        CaseManager().resultCleared.connect(self._clear)

    def _disconnectSignalsSlots(self):
        self._project.projectClosed.disconnect(self._projectClosed)
        self._project.solverStatusChanged.disconnect(self._solverStatusChanged)
        CaseManager().caseLoaded.disconnect(self._caseLoaded)
        CaseManager().caseCleared.disconnect(self._clear)
        CaseManager().resultCleared.disconnect(self._clear)

    @qasync.asyncSlot()
    async def _caseLoaded(self):
        self._clear()
        self._startMonitor()

    def _projectClosed(self):
        self._stopMonitor()
        self._clear()

    @qasync.asyncSlot()
    async def _solverStatusChanged(self, status, name, liveStatusChanged):
        if status == SolverStatus.NONE:
            self._deletedMonitors = self._monitors
            self._clear()
        elif status == SolverStatus.RUNNING:
            self._clear()
            self._startMonitor()
        elif status == SolverStatus.ENDED or status == SolverStatus.ERROR:
            self._stopMonitor()

    def _clear(self):
        for monitor in self._monitors.values():
            monitor.stop()
            monitor.deleteChart()

        self._monitors = {}

    def _startMonitor(self):
        maxX = calculateMaxX()

        for configurations in MonitorService.getForceMonitors():
            self._addMonitor(
                ForceMonitor(configurations, self._createChart(maxX), self._createChart(maxX), self._createChart(maxX)))
        for configurations in MonitorService.getPointMonitors():
            self._addMonitor(PointMonitor(configurations, self._createChart(maxX)))
        for configurations in MonitorService.getSurfaceMonitors():
            self._addMonitor(SurfaceMonitor(configurations, self._createChart(maxX)))
        for configurations in MonitorService.getVolumeMonitors():
            self._addMonitor(VolumeMonitor(configurations, self._createChart(maxX)))

    def _stopMonitor(self):
        if self._monitors:
            for name in self._monitors:
                self._monitors[name].stop()

    def _addMonitor(self, monitor):
        self._monitors[monitor.name] = monitor
        monitor.stopped.connect(self._removeMonitor)
        monitor.start()

    def _removeMonitor(self, name):
        if self._deletedMonitors and name in self._deletedMonitors:
            del self._deletedMonitors[name]

    def _createChart(self, maxX):
        chart = ChartWidget(maxX)
        chart.setFixedSize(500, 300)
        chart.layout().setContentsMargins(QMargins(15, 10, 15, 15))

        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.white)
        chart.setAutoFillBackground(True)
        chart.setPalette(pal)

        self._chartsLayout.addWidget(chart)

        return chart

    def closeEvent(self, event):
        self._disconnectSignalsSlots()

        super().closeEvent(event)

class MonitorDock(CDockWidget):
    def __init__(self):
        super().__init__(self._title())

        self._widget = MonitorView()
        self.setWidget(self._widget)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.setWindowTitle(self._title())

        super().changeEvent(event)

    def _title(self):
        return QCoreApplication.translate('MonitorDock', 'Monitor')
