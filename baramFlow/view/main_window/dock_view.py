#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QMargins
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6QtAds import CDockManager, DockWidgetArea

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

        self._dockArea = self._addDock(self._consoleDock)
        self._addDock(self._renderingDock)
        self._addDock(self._chartDock)
        self._addDock(self._monitorDock)

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

        self._consoleDock.widget().close()
        self._renderingDock.widget().close()
        self._chartDock.widget().close()
        self._monitorDock.widget().close()

        super().close()

    def _addDock(self, dock):
        area = self._dockManager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, dock, self._dockArea)
        self._menu.addAction(dock.toggleViewAction())

        return area


