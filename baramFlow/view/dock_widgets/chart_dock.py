#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import pandas as pd
import qasync
from PySide6.QtCore import QMargins, QCoreApplication, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6QtAds import CDockWidget

from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.project import Project, SolverStatus
from baramFlow.coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver_info_manager import SolverInfoManager
from baramFlow.view.widgets.chart_wigdet import ChartWidget


class ChartView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._solverInfoManager = SolverInfoManager()
        self._project = Project.instance()

        self._connectSignalsSlots()

        if GeneralDB.isTimeTransient():
            timeSteppingMethod = coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeSteppingMethod')
            if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
                # 50 Residual points
                timeStep = float(
                    coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/timeStepSize'))
                self._width = timeStep * 50
            else:
                # 10% of total case time
                endTime = float(
                    coredb.CoreDB().getValue(RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions/endTime'))
                self._width = endTime / 10
        else:
            # 50 Residual points
            self._width = 50

        self._chart = ChartWidget(self._width)
        self._chart.setTitle('Residuals')
        self._chart.logScaleOn()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(QMargins(40, 40, 40, 40))
        layout.addWidget(self._chart)

        self.setStyleSheet('background-color: white')

    def _connectSignalsSlots(self):
        self._solverInfoManager.residualsUpdated.connect(self._updated)
        self._solverInfoManager.flushed.connect(self._flushed)

        self._project.projectClosed.connect(self._projectClosed)
        self._project.solverStatusChanged.connect(self._solverStatusChanged)

        CaseManager().caseLoaded.connect(self._caseLoaded)
        CaseManager().caseCleared.connect(self._caseCleared)

    def _disconnectSignalsSlots(self):
        self._solverInfoManager.residualsUpdated.disconnect(self._updated)
        self._solverInfoManager.flushed.disconnect(self._flushed)

        self._project.projectClosed.disconnect(self._projectClosed)
        self._project.solverStatusChanged.disconnect(self._solverStatusChanged)

        CaseManager().caseLoaded.disconnect(self._caseLoaded)
        CaseManager().caseCleared.disconnect(self._caseCleared)

    def startDrawing(self):
        self._solverInfoManager.startCollecting(Path(FileSystem.caseRoot()).resolve(), coredb.CoreDB().getRegions())

    def stopDrawing(self):
        self._solverInfoManager.stopCollecting()

    @qasync.asyncSlot()
    async def _caseLoaded(self):
        self._chart.clear()
        if CaseManager().isRunning() or CaseManager().isEnded():
            self.startDrawing()

    def _caseCleared(self):
        self._chart.clear()

    def _projectClosed(self):
        self.stopDrawing()

    @qasync.asyncSlot()
    async def _solverStatusChanged(self, status, name, liveStatusChanged):
        if status == SolverStatus.NONE:
            self._chart.clear()
        elif status == SolverStatus.RUNNING:
            self.startDrawing()
        else:
            self.stopDrawing()

    def _updated(self, data: pd.DataFrame):
        self._chart.dataUpdated(data)

    def _flushed(self):
        self._chart.fitChart()

    def closeEvent(self, event):
        self._disconnectSignalsSlots()

        super().closeEvent(event)


class ChartDock(CDockWidget):
    def __init__(self):
        super().__init__(self._title())

        self._widget = ChartView()
        self.setWidget(self._widget)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.setWindowTitle(self._title())

        super().changeEvent(event)

    def _title(self):
        return QCoreApplication.translate('ChartDock', 'Residuals')
