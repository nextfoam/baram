#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout, QWidget, QTextBrowser
from PySide6.QtCore import Qt

from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

from openfoam.solver_info_manager import getSolverInfoManager
from .tabified_dock import TabifiedDock


class ChartDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._textView = None

        self._lines = {}

        self.setWindowTitle(self.tr("Chart"))
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._widget = QWidget()
        self.setWidget(self._widget)

        layout = QtWidgets.QVBoxLayout(self._widget)

        self.static_canvas = FigureCanvas(Figure(figsize=(5, 3)))
        # Ideally one would use self.addToolBar here, but it is slightly
        # incompatible between PyQt6 and other bindings, so we just add the
        # toolbar as a plain widget instead.
        layout.addWidget(NavigationToolbar(self.static_canvas, self))
        layout.addWidget(self.static_canvas)

        self._static_ax = self.static_canvas.figure.subplots()
        self._static_ax.set_yscale('log')

        self.lines1 = None

        self.solverInfoManager = getSolverInfoManager(Path('./multiRegionHeater').resolve())

        self.solverInfoManager.updated.connect(self.updated)

        self.startDrawing()

    def startDrawing(self):
        self.solverInfoManager.startCollecting()

    def updated(self, data):
        for df in data:
            print('output ')
            columns = list(filter(lambda x: x.endswith('_initial'),
                             df.columns.values.tolist()))
            print('output ')
            timeMin = df.first_valid_index()
            timeMax = df.last_valid_index()
            print(f'time range ({timeMin}, {timeMax})')

            d = df.reset_index()  # "Time" is back to a column to serve as X value

            for c in columns:
                if c not in self._lines:
                    print('newLine '+c)
                    self._lines[c], = self._static_ax.plot('Time', c, '', label=c, data=d)
                else:
                    print('updateLine ' + c)
                    self._lines[c].set_data(d[['Time', c]].to_numpy().transpose())

        self._static_ax.set_xlim(None, timeMax+1)
        self._static_ax.legend()
        self.static_canvas.draw()



