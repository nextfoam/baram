#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QMargins
from PySide6.QtWidgets import QVBoxLayout, QWidget
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

        self._consoleDock = ConsoleDock()
        self._renderingDock = RenderingDock()
        self._chartDock = ChartDock()
        self._monitorDock = MonitorDock()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(QMargins(0, 0, 0, 0))
        layout.addWidget(self._dockManager)

        dockArea = self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, self._consoleDock)
        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, self._renderingDock, dockArea)
        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, self._chartDock, dockArea)
        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, self._monitorDock, dockArea)

    def consoleView(self):
        return self._consoleDock.widget()

    def renderingView(self):
        return self._renderingDock.widget()

    def showConsoleDock(self):
        self._consoleDock.raise_()

    def showRenderingDock(self):
        self._renderingDock.raise_()

    def showChartDock(self):
        self._chartDock.raise_()

    def close(self):
        self._dockManager.deleteLater()
        self._renderingDock.widget().close()
        super().close()

    def _addDock(self, name, widget):
        dock = CDockWidget(name)
        dock.setWidget(widget)
        self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, dock, self._dockArea)
        self._menu.addAction(dock.toggleViewAction())

        return dock


