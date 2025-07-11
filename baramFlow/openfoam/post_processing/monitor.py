#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

import pandas as pd
from PySide6.QtCore import QThread, QObject, QTimer, Signal, Qt

from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, Field
from baramFlow.coredb.project import Project
from baramFlow.coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
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

    def createReader(self, rname, fileName, extension):
        self._reader = PostFileReader(self._name, rname, fileName, extension)

    def startMonitor(self):
        changedFiles = self._reader.chagedFiles()
        while not changedFiles and CaseManager().isRunning():
            time.sleep(0.5)
            changedFiles = self._reader.chagedFiles()

        if changedFiles:
            for path in changedFiles[1:]:
                data = self._reader.readDataFrame(path)
                self.dataUpdated.emit(data)

            self._reader.openMonitor()
            self._monitor()

            if CaseManager().isRunning():
                self._timer = QTimer()
                self._timer.setInterval(500)
                self._timer.timeout.connect(self._monitor)
                self._timer.start()
            else:
                self.flushed.emit()
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
        self._rname = ''
        self._thread = None
        self._worker = None
        self._showChart = True

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
        self._worker.createReader(self._rname, self.fileName, self.extension)
        self._worker.dataUpdated.connect(self._updateChart, type=Qt.ConnectionType.QueuedConnection)
        self._worker.stopped.connect(self._stopped, type=Qt.ConnectionType.QueuedConnection)
        self._worker.flushed.connect(self._fitChart, type=Qt.ConnectionType.QueuedConnection)

        self._thread.started.connect(self._worker.startMonitor, type=Qt.ConnectionType.QueuedConnection)
        self._thread.start()

        self.startWorker.connect(self._worker.startMonitor, type=Qt.ConnectionType.QueuedConnection)
        self.stopWorker.connect(self._worker.stopMonitor, type=Qt.ConnectionType.QueuedConnection)

    def start(self):
        if self._worker:
            self.startWorker.emit()
        else:
            self.startThread()

    def stop(self):
        self.stopWorker.emit()

    def quit(self):
        self.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

    def _updateChart(self, data):
        pass

    def _fitChart(self):
        pass

    def _stopped(self):
        self.stopped.emit(self._name)


class ForceMonitor(Monitor):
    def __init__(self, name, chart1, chart2, chart3):
        super().__init__(name)

        db = coredb.CoreDB()
        xpath = MonitorDB.getForceMonitorXPath(name)

        self._showChart = db.getValue(xpath + '/showChart') == 'true'
        self._rname = db.getValue(xpath + '/region')
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
        self._chart1.dataAppended(pd.DataFrame(data, columns=['Cd']))
        self._chart2.dataAppended(pd.DataFrame(data, columns=['Cl']))
        self._chart3.dataAppended(pd.DataFrame(data, columns=['CmPitch']).rename(columns={'CmPitch': 'Cm'}))

    def _fitChart(self):
        self._chart1.fitChart()
        self._chart2.fitChart()
        self._chart3.fitChart()


class PointMonitor(Monitor):
    def __init__(self, name, chart):
        super().__init__(name)

        db = coredb.CoreDB()
        self._xpath = MonitorDB.getPointMonitorXPath(name)

        self._showChart = db.getValue(self._xpath + '/showChart') == 'true'
        self._rname = db.getValue(self._xpath + '/region')
        self._chart = chart

        self._legend = FieldHelper.DBFieldKeyToText(Field(db.getValue(self._xpath + '/field/field')),
                                                    db.getValue(self._xpath + '/field/fieldID'))

        self._chart.setTitle(name)

    @property
    def fileName(self):
        db = coredb.CoreDB()
        return FieldHelper.DBFieldKeyToField(Field(db.getValue(self._xpath + '/field/field')),
                                             db.getValue(self._xpath + '/field/fieldID'))

    @property
    def extension(self):
        return ''

    def _updateChart(self, data):
        data.columns = [self._legend]
        self._chart.dataAppended(data)

    def _fitChart(self):
        self._chart.fitChart()


class SurfaceMonitor(Monitor):
    def __init__(self, name, chart):
        super().__init__(name)

        db = coredb.CoreDB()
        xpath = MonitorDB.getSurfaceMonitorXPath(name)

        self._showChart = db.getValue(xpath + '/showChart') == 'true'
        self._rname = BoundaryDB.getBoundaryRegion(db.getValue(xpath + '/surface'))
        self._chart = chart

        self._legend = None

        reportType = SurfaceReportType(db.getValue(xpath + '/reportType'))
        self._legend = MonitorDB.surfaceReportTypeToText(reportType)
        if reportType not in (SurfaceReportType.MASS_FLOW_RATE, SurfaceReportType.VOLUME_FLOW_RATE):
            self._legend += ' ' + FieldHelper.DBFieldKeyToText(Field(db.getValue(xpath + '/field/field')),
                                                               db.getValue(xpath + '/field/fieldID'))

        self._chart.setTitle(name)

    @property
    def fileName(self):
        return 'surfaceFieldValue'

    def _updateChart(self, data):
        data.columns = [self._legend]
        self._chart.dataAppended(data)

    def _fitChart(self):
        self._chart.fitChart()


class VolumeMonitor(Monitor):
    def __init__(self, name, chart):
        super().__init__(name)

        db = coredb.CoreDB()
        xpath = MonitorDB.getVolumeMonitorXPath(name)

        self._showChart = db.getValue(xpath + '/showChart') == 'true'
        self._rname = CellZoneDB.getCellZoneRegion(db.getValue(xpath + '/volume'))
        self._chart = chart

        self._legend = (f"{MonitorDB.volumeReportTypeToText(VolumeReportType(db.getValue(xpath + '/reportType')))}"
                        f" {FieldHelper.DBFieldKeyToText(Field(db.getValue(xpath + '/field/field')), db.getValue(xpath + '/field/fieldID'))}")

        self._chart.setTitle(name)

    @property
    def fileName(self):
        return 'volFieldValue'

    def _updateChart(self, data):
        data.columns = [self._legend]
        self._chart.dataAppended(data)

    def _fitChart(self):
        self._chart.fitChart()

