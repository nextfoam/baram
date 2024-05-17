#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QMargins
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6QtAds import CDockManager, CDockWidget, DockWidgetArea

from baramFlow.view.dock_widgets.chart_dock import ChartDock
from baramFlow.view.dock_widgets.console_dock import ConsoleDock
from baramFlow.view.dock_widgets.monitor_dock import MonitorDock
from baramFlow.view.dock_widgets.rendering_dock import RenderingDock


class DockView(QWidget):
    def __init__(self, menu):
        super().__init__()

        self._dockManager = CDockManager(self)
        self._dockArea = None
        self._menu = menu
        self._setupUi()

        self._consoleDock = ConsoleDock()
        self._renderingDock = RenderingDock()
        self._chartDock = ChartDock()
        self._monitorDock = MonitorDock()

        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, self._consoleDock, self._dockArea)
        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, self._renderingDock, self._dockArea)
        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, self._chartDock, self._dockArea)
        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, self._monitorDock, self._dockArea)

    def renderingView(self):
        return self._renderingDock.widget()

    def showChartDock(self):
        self._chartDock.raise_()

    def showRenderingDock(self):
        self._renderingDock.raise_()

    def close(self):
        self._dockManager.deleteLater()
        self._renderingDock.widget().close()
        super().close()

    def _setupUi(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(QMargins(0, 0, 0, 0))
        layout.addWidget(self._dockManager)

        emptyDock = CDockWidget("emptyDock")
        emptyDock.setWidget(QLabel())
        emptyDock.setFeature(CDockWidget.NoTab, True)
        self._dockArea = self._dockManager.setCentralWidget(emptyDock)

    def _addDock(self, name, widget):
        dock = CDockWidget(name)
        dock.setWidget(widget)
        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, dock, self._dockArea)
        self._menu.addAction(dock.toggleViewAction())

        return dock


