#!/usr/bin/env python
# -*- coding: utf-8 -*-


import pandas as pd
from PySide6.QtCore import QThread, QObject, QTimer, Signal, Qt

from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.coredb import CoreDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.coredb.project import Project
from baramFlow.coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.openfoam.post_processing.post_file_reader import PostFileReader


def calculateMaxX():
    if GeneralDB.isTimeTransient():
        timeSteppingMethod = coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeSteppingMethod')
        if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
            # 50 Residual points
            timeStep = float(
                coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeStepSize'))
            maxX = timeStep * 50
        else:
            # 10% of total case time
            endTime = float(
                coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/endTime'))
            maxX = endTime / 10
    else:
        # 50 Residual points
        maxX = 50

    return maxX


class Worker(QObject):
    dataUpdated = Signal(pd.DataFrame)
    stopped = Signal()
    flushed = Signal()

    def __init__(self, name):
        super().__init__()
        self._project = Project.instance()
        self._name = name
        self._reader = None
        self._timer = None
        self._appending = False

    def createReader(self, rname, functionName, fileName, extension):
        self._reader = PostFileReader(self._name, rname, functionName, fileName, extension)

    def startMonitor(self):
        if self._timer is not None:
            return

        changedFiles = self._reader.changedFiles()
        if changedFiles:
            for path in changedFiles:
                data = self._reader.readDataFrame(path)
                if not data.empty:
                    self.dataUpdated.emit(data)

        self._appending = False

        if CaseManager().isRunning():
            self._timer = QTimer()
            self._timer.setInterval(500)
            self._timer.timeout.connect(self._monitor)
            self._timer.start()
        else:
            self.flushed.emit()

    def stopMonitor(self):
        if self._timer:
            self._timer.stop()
            self._timer = None
            self._monitor()
            self._reader.closeMonitor()
            self.stopped.emit()

    def _findChangingFile(self):
        if self._reader.changedFiles():
            self._appending = True

        return self._appending

    def _monitor(self):
        if not self._appending:
            if self._findChangingFile():
                self._reader.openMonitor()
            else:
                return

        data = self._reader.readTailDataFrame()
        if data is not None:
            self.dataUpdated.emit(data)


class Monitor(QObject):
    startWorker = Signal()
    stopWorker = Signal()
    stopped = Signal(str)

    def __init__(self, name, functionName):
        super().__init__()

        self._name = name
        self._functionName = functionName
        self._rname = ''
        self._thread = None
        self._worker = None
        self._showChart = True

    @property
    def name(self):
        return self._name

    @property
    def functionName(self):
        return self._functionName

    @property
    def fileName(self):
        return None

    @property
    def extension(self):
        return '.dat'

    def visibility(self):
        return self._showChart

    def start(self):
        if self._thread is not None:
            self.stop()

        self._thread = QThread()
        self._worker = Worker(self.name)
        self._worker.moveToThread(self._thread)
        self._worker.createReader(self._rname, self._functionName, self.fileName, self.extension)
        self._worker.dataUpdated.connect(self._updateChart, type=Qt.ConnectionType.QueuedConnection)
        self._worker.stopped.connect(self._stopped, type=Qt.ConnectionType.QueuedConnection)
        self._worker.flushed.connect(self._fitChart, type=Qt.ConnectionType.QueuedConnection)

        # self._thread.started.connect(self._worker.startMonitor, type=Qt.ConnectionType.QueuedConnection)
        self._thread.start()

        self.startWorker.connect(self._worker.startMonitor, type=Qt.ConnectionType.QueuedConnection)
        self.stopWorker.connect(self._worker.stopMonitor, type=Qt.ConnectionType.QueuedConnection)

        self.startWorker.emit()

    def stop(self):
        if self._thread is None:
            return

        self.stopWorker.emit()

        self._thread.quit()
        self._thread.wait()

        self._worker = None
        self._thread = None

    def _updateChart(self, data):
        pass

    def _fitChart(self):
        pass

    def _stopped(self):
        self.stopped.emit(self._name)


class ForceMonitor(Monitor):
    def __init__(self, configuration, chart1, chart2, chart3):
        super().__init__(configuration.monitorBase.name, configuration.monitorBase.functionName)

        self._showChart = configuration.monitorBase.showChart
        self._rname = configuration.region

        self._chart1 = chart1
        self._chart2 = chart2
        self._chart3 = chart3

        self._chart1.setTitle(f'{self._name} - Cd')
        self._chart2.setTitle(f'{self._name} - Cl')
        self._chart3.setTitle(f'{self._name} - Cm')

    @property
    def fileName(self):
        return 'coefficient'

    def deleteChart(self):
        if self._chart1 is not None:
            self._chart1.deleteLater()
            self._chart1 = None

        if self._chart2 is not None:
            self._chart2.deleteLater()
            self._chart2 = None

        if self._chart3 is not None:
            self._chart3.deleteLater()
            self._chart3 = None

    def _updateChart(self, data):
        self._chart1.dataAppended(pd.DataFrame(data, columns=['Cd']))
        self._chart2.dataAppended(pd.DataFrame(data, columns=['Cl']))
        self._chart3.dataAppended(pd.DataFrame(data, columns=['CmPitch']).rename(columns={'CmPitch': 'Cm'}))

    def _fitChart(self):
        self._chart1.fitChart()
        self._chart2.fitChart()
        self._chart3.fitChart()


class PointMonitor(Monitor):
    def __init__(self, configuration, chart):
        super().__init__(configuration.monitorBase.name, configuration.monitorBase.functionName)

        self._showChart = configuration.monitorBase.showChart
        self._rname = configuration.region

        self._field = configuration.field
        self._legend = self._field.displayText()

        self._chart = chart
        self._chart.setTitle(self._name)

    @property
    def fileName(self):
        return self._field.openfoamField()
        # field = self._field
        # if field.type == FieldType.VECTOR:
        #     return getSolverComponentName(field, self._field.component)
        # return getSolverFieldName(field)

    def deleteChart(self):
        if self._chart is not None:
            self._chart.deleteLater()
            self._chart = None

    @property
    def extension(self):
        return ''

    def _updateChart(self, data):
        data.columns = [self._legend]
        self._chart.dataAppended(data)

    def _fitChart(self):
        self._chart.fitChart()


class SurfaceMonitor(Monitor):
    def __init__(self, configuration, chart):
        super().__init__(configuration.monitorBase.name, configuration.monitorBase.functionName)

        self._showChart = configuration.monitorBase.showChart
        self._rname = BoundaryDB.getBoundaryRegion(
            CoreDB().getValue(MonitorDB.getSurfaceMonitorXPath(self._name) + '/surface'))

        self._chart = chart
        self._chart.setTitle(self._name)

        reportType = configuration.reportType
        self._legend = MonitorDB.surfaceReportTypeToText(reportType)
        if reportType not in (SurfaceReportType.MASS_FLOW_RATE, SurfaceReportType.VOLUME_FLOW_RATE):
            self._legend += ' ' + configuration.field.displayText()

    @property
    def fileName(self):
        return 'surfaceFieldValue'

    def deleteChart(self):
        if self._chart is not None:
            self._chart.deleteLater()
            self._chart = None

    def _updateChart(self, data):
        data.columns = [self._legend]
        self._chart.dataAppended(data)

    def _fitChart(self):
        self._chart.fitChart()


class VolumeMonitor(Monitor):
    def __init__(self, configuration, chart):
        super().__init__(configuration.monitorBase.name, configuration.monitorBase.functionName)

        self._showChart = configuration.monitorBase.showChart
        self._rname = CellZoneDB.getCellZoneRegion(
            CoreDB().getValue(MonitorDB.getVolumeMonitorXPath(self._name) + '/volume'))

        self._legend = (f"{MonitorDB.volumeReportTypeToText(configuration.reportType)}"
                        f" {configuration.field.displayText()}")

        self._chart = chart
        self._chart.setTitle(self._name)

    @property
    def fileName(self):
        return 'volFieldValue'

    def deleteChart(self):
        if self._chart is not None:
            self._chart.deleteLater()
            self._chart = None

    def _updateChart(self, data):
        data.columns = [self._legend]
        self._chart.dataAppended(data)

    def _fitChart(self):
        self._chart.fitChart()

