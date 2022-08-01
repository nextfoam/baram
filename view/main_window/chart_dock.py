#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout, QWidget, QTextBrowser
from PySide6.QtCore import Qt

import numpy as np

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

        self._canvas = FigureCanvas(Figure(figsize=(5, 3)))
        self._canvas.mpl_connect('scroll_event', self.onScroll)
        # Ideally one would use self.addToolBar here, but it is slightly
        # incompatible between PyQt6 and other bindings, so we just add the
        # toolbar as a plain widget instead.
        #layout.addWidget(NavigationToolbar(self.canvas, self))
        layout.addWidget(self._canvas)

        self._ax = self._canvas.figure.subplots()
        self._ax.set_yscale('log')

        self.solverInfoManager = getSolverInfoManager(Path('./multiRegionHeater').resolve())

        self.solverInfoManager.updated.connect(self.updated)

        self.startDrawing()

    def startDrawing(self):
        self.solverInfoManager.startCollecting()

    def updated(self, data):
        for df in data:
            columns = list(filter(lambda x: x.endswith('_initial'),
                                  df.columns.values.tolist()))

            timeMin = df.first_valid_index()
            timeMax = df.last_valid_index()

            d = df.reset_index()  # "Time" is back to a column to serve as X value

            for c in columns:
                if c not in self._lines:
                    self._lines[c], = self._ax.plot('Time', c, '', label=c[:-8], data=d)
                else:
                    self._lines[c].set_data(d[['Time', c]].to_numpy().transpose())

        self._ax.set_xlim(None, timeMax)
        self._ax.legend()
        self._canvas.draw()

    def onScroll(self, event):
        print(f'mouse event {event.step}')
        minX, maxX = self._ax.get_xlim()
        scale = np.power(1.05, -event.step)
        print(f'scale {scale}')
        left = maxX - (maxX-minX) * scale
        self._ax.set_xlim([left, maxX])
        self._ax.relim(visible_only=True)
        self._ax.set_autoscaley_on(True)
        self._ax.autoscale_view(scalex=False, scaley=True)

        self._canvas.draw()  # force re-draw the next time the GUI refreshes



