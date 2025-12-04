#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from PySide6.QtWidgets import QDialog, QMessageBox

import pyqtgraph as pg

from .piecewise_linear_dialog_ui import Ui_PiecewiseLinearDialog


COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', "#1f1b24", '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


class PiecewiseLinearDialog(QDialog):
    def __init__(self, parent, chartTitle: str, indexName: str, indexUnit: str, dataNames: list[str], dataUnit: str, data: Optional[list[list[float]]] = None):
        super().__init__(parent)

        self._ui = Ui_PiecewiseLinearDialog()
        self._ui.setupUi(self)

        indexLabel = f'{indexName} ({indexUnit})' if indexUnit else indexName
        dataLabel  = f'{", ".join(dataNames)} ({dataUnit})' if dataUnit else f'{", ".join(dataNames)}'

        plotWidget = self._ui.plotWidget
        plotWidget.setTitle(chartTitle, color='#5f5f5f', size='12pt')
        plotWidget.setLabel('bottom', indexLabel)
        plotWidget.setLabel('left', dataLabel)
        plotWidget.showGrid(x=True, y=True)
        plotWidget.setBackground('w')
        plotWidget.setMinimumHeight(150)

        plotItem: pg.PlotItem = plotWidget.getPlotItem()
        plotItem.getAxis('left').setTextPen('#5f5f5f')
        plotItem.getAxis('bottom').setTextPen('#5f5f5f')

        self._plotDataItems: list[pg.PlotDataItem] = []
        for i in range(len(dataNames)):
            self._plotDataItems.append(plotWidget.plot(
                [], [],  # Start with empty data
                pen={'color': COLORS[i], 'width': 2},  # Line style
                symbol='o',  # Circle markers
                symbolSize=4,
                symbolBrush=pg.mkBrush(color=COLORS[i]),  # Fill color for markers
                symbolPen={'color': COLORS[i], 'width': 1}  # Outline for markers
            ))

        tableLabels = [indexLabel] + [f'{name} ({dataUnit})' if dataUnit else name for name in dataNames]
        self._ui.tableWidget.setup(tableLabels, data)

        self._connectSignalsSlots()

        self._updateChart()

    def _connectSignalsSlots(self):
        self._ui.tableWidget.dataUpdated.connect(self._updateChart)

    def _updateChart(self):
        data = self._ui.tableWidget.getData()
        data = [list(x) for x in zip(*data)]  # transpose the data to use it in pyqtgraph
        for i in range(len(data)-1):
            self._plotDataItems[i].setData(data[0], data[i+1])

    def accept(self):
        if not self._ui.tableWidget.isDataComplete(ascendingFirstColumn=True):
            QMessageBox.warning(self,
                self.tr('Table value integrity error'),
                self.tr(f'Table values must conform to the rules below:<br/>'
                        f'  - The values in the first column must be in ascending order.<br/>'
                        f'  - Empty cells are not allowed within the data range.'))
            return

        super().accept()

    def getData(self):
        return self._ui.tableWidget.getData()
