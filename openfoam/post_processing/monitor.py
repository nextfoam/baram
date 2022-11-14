#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

import pandas as pd
from PySide6.QtCore import QThread, QObject, QTimer, Signal, Qt

from coredb import coredb
from coredb.project import Project
from coredb.monitor_db import MonitorDB
from coredb.general_db import GeneralDB
from coredb.run_calculation_db import RunCalculationDB
from coredb.monitor_db import FieldHelper
from openfoam.post_processing.post_file_reader import PostFileReader


def calculateMaxX():
    if GeneralDB.isTimeTransient():
        # 10% of total case time
        endTime = float(coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/endTime'))
        maxX = endTime / 10
    else:
        # 10% of total iteration count or iteration count if it is less than MIN_COUNT
        MIN_COUNT = 100
        count = int(coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/numberOfIterations'))
        if count < MIN_COUNT:
            maxX = count
        else:
            maxX = MIN_COUNT + count / 10

    return maxX


class Worker(QObject):
    dataUpdated = Signal(pd.DataFrame)
    stopped = Signal()

    def __init__(self, name):
        super().__init__()
        self._name = name
        self._reader = None
        self._timer = None

    def createReader(self, fileName, extension):
        self._reader = PostFileReader(self._name, fileName, extension)

    def startMonitor(self):
        changedFiles = None
        while not changedFiles:
            if changedFiles := self._reader.chagedFiles():
                for path in changedFiles[1:]:
                    data = self._reader.readDataFrame(path)
                    self.dataUpdated.emit(data)
            time.sleep(1)

        self._reader.openMonitor()
        self._monitor()

        if Project.instance().isSolverRunning():
            self._timer = QTimer()
            self._timer.setInterval(500)
            self._timer.timeout.connect(self._monitor)
            self._timer.start()
        else:
            self._reader.closeMonitor()

    def stopMonitor(self):
        if self._timer:
            self._timer.stop()
            self._timer = None
            self._monitor()
            self._reader.closeMonitor()
            self.stopped.emit()

    def _monitor(self):
        data = self._reader.readTailDataFrame()
        if data is not None:
            self.dataUpdated.emit(data)

class Monitor(QObject):
    startWorker = Signal()
    stopWorker = Signal()
    stopped = Signal(str)

    def __init__(self, name):
        super().__init__()

        self._name = name
        self._thread = None
        self._worker = None
        self._showChart = True
        self._running = False

    @property
    def name(self):
        return self._name

    @property
    def fileName(self):
        return None

    @property
    def extension(self):
        return '.dat'

    def visibility(self):
        return self._showChart

    def startThread(self):
        self._thread = QThread()
        self._worker = Worker(self.name)
        self._worker.moveToThread(self._thread)
        self._worker.createReader(self.fileName, self.extension)
        self._worker.dataUpdated.connect(self._updateChart, type=Qt.ConnectionType.QueuedConnection)
        self._worker.stopped.connect(self._stopped, type=Qt.ConnectionType.QueuedConnection)

        self._thread.started.connect(self._worker.startMonitor, type=Qt.ConnectionType.QueuedConnection)
        self._thread.start()

        self.startWorker.connect(self._worker.startMonitor, type=Qt.ConnectionType.QueuedConnection)
        self.stopWorker.connect(self._worker.stopMonitor, type=Qt.ConnectionType.QueuedConnection)

    def start(self):
        if self._worker:
            self.startWorker.emit()
        else:
            self.startThread()

        self._running = True

    def stop(self):
        self._running = False
        self.stopWorker.emit()

    def quit(self):
        self.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

    def _updateChart(self, data):
        pass

    def _stopped(self):
        self.stopped.emit(self._name)

class ForceMonitor(Monitor):
    def __init__(self, name, chart1, chart2, chart3):
        super().__init__(name)

        self._showChart = coredb.CoreDB().getValue(MonitorDB.getForceMonitorXPath(name) + '/showChart') == 'true'
        self._chart1 = chart1
        self._chart2 = chart2
        self._chart3 = chart3

        chart1.setTitle(f'{name} - Cd')
        chart2.setTitle(f'{name} - Cl')
        chart3.setTitle(f'{name} - Cm')

    @property
    def fileName(self):
        return 'coefficient'

    def _updateChart(self, data):
        if self._running:
            self._chart1.appendData(pd.DataFrame(data, columns=['Cd']))
            self._chart2.appendData(pd.DataFrame(data, columns=['Cl']))
            self._chart3.appendData(pd.DataFrame(data, columns=['CmPitch']).rename(columns={'CmPitch': 'Cm'}))


class PointMonitor(Monitor):
    def __init__(self, name, chart):
        super().__init__(name)

        self._xpath = MonitorDB.getPointMonitorXPath(name)
        self._showChart = coredb.CoreDB().getValue(self._xpath + '/showChart') == 'true'
        self._chart = chart

        self._chart.setTitle(name)

    @property
    def fileName(self):
        return FieldHelper.DBFieldKeyToField(coredb.CoreDB().getValue(self._xpath + '/field/field'),
                                             coredb.CoreDB().getValue(self._xpath + '/field/mid'))

    @property
    def extension(self):
        return ''

    def _updateChart(self, data):
        if self._running:
            self._chart.appendData(data)


class SurfaceMonitor(Monitor):
    def __init__(self, name, chart):
        super().__init__(name)

        self._showChart = coredb.CoreDB().getValue(MonitorDB.getSurfaceMonitorXPath(name) + '/showChart') == 'true'
        self._chart = chart

        self._chart.setTitle(name)

    @property
    def fileName(self):
        return 'surfaceFieldValue'

    def _updateChart(self, data):
        if self._running:
            self._chart.appendData(data)


class VolumeMonitor(Monitor):
    def __init__(self, name, chart):
        super().__init__(name)

        self._showChart = coredb.CoreDB().getValue(MonitorDB.getVolumeMonitorXPath(name) + '/showChart') == 'true'
        self._chart = chart

        self._chart.setTitle(name)

    @property
    def fileName(self):
        return 'volFieldValue'

    def _updateChart(self, data):
        if self._running:
            self._chart.appendData(data)
