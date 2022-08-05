#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import psutil
import signal
import time
import platform

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from coredb import coredb
from coredb.project import Project, SolverStatus
from openfoam.run import launchSolver
from openfoam.case_generator import CaseGenerator
from openfoam.system.fv_solution import FvSolution
from openfoam.system.control_dict import ControlDict
from openfoam.system.fv_schemes import FvSchemes
import openfoam.solver
from openfoam.file_system import FileSystem
from .process_information_page_ui import Ui_ProcessInformationPage

SOLVER_CHECK_INTERVAL = 3000


class ProcessInformationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ProcessInformationPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._project = Project.instance()

        self._solvers = openfoam.solver.findSolvers()
        self._caseRoot = FileSystem.caseRoot()

        self._connectSignalsSlots()

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        self._updateStatus()

        return super().showEvent(ev)

    def save(self):
        pass

    def _connectSignalsSlots(self):
        self._ui.startCalculation.clicked.connect(self._startCalculationClicked)
        self._ui.cancelCalculation.clicked.connect(self._cancelCalculationClicked)
        self._ui.saveAndStopCalculation.clicked.connect(self._saveAndStopCalculationClicked)
        self._ui.updateConfiguration.clicked.connect(self._updateConfigurationClicked)
        self._project.statusChanged.connect(self._updateStatus)

    def _startCalculationClicked(self):
        CaseGenerator().generateFiles()

        controlDict = ControlDict().build()
        controlDict.asDict()['startFrom'] = 'latestTime'
        controlDict.asDict()['stopAt'] = 'endTime'
        controlDict.write()

        numCores = self._db.getValue('.//runCalculation/parallel/numberOfCores')

        process = launchSolver(self._solvers[0], Path(self._caseRoot), int(numCores))
        self._project.setSolverProcess(process)

    def _cancelCalculationClicked(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'noWriteNow'
        controlDict.write()

        self._timer = QTimer()
        self._timer.setInterval(SOLVER_CHECK_INTERVAL)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._waitingStop)
        self._timer.start()

    def _waitingStop(self):
        if self._project.solverStatus() == SolverStatus.RUNNING:
            ps = psutil.Process(pid=self._project.pid)
            if ps.create_time() == self._project.startTime:
                if platform.system() == "Windows":
                    ps.send_signal(signal.CTRL_C_EVENT)
                elif platform.system() == "Linux":
                    ps.send_signal(signal.SIGTERM)
                    ps.wait()   # Temporary code
                else:
                    raise Exception(self.tr('Unsupported OS'))

    def _saveAndStopCalculationClicked(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'writeNow'
        controlDict.write()

    def _updateConfigurationClicked(self):
        regions = self._db.getRegions()
        for rname in regions:
            FvSchemes(rname).build().write()
            FvSolution(rname).build().write()
        ControlDict().build().write()

    def _updateStatus(self):
        status = self._project.solverStatus()

        if status == SolverStatus.NONE:
            text = self.tr('Not Running')
        elif status == SolverStatus.WAITING:
            text = self.tr('Waiting')
        elif status == SolverStatus.RUNNING:
            text = self.tr('Running')
        else:
            text = '-'

        pid, startTime = self._project.solverProcess()
        if startTime:
            createTime = time.strftime("%Y-%m-%d, %H:%M:%S", time.localtime(startTime))
        else:
            createTime = '-'

        self._ui.id.setText(str(pid) if pid else '-')
        self._ui.createTime.setText(createTime)
        self._ui.status.setText(text)

        self._ui.startCalculation.setVisible(status == SolverStatus.NONE)
        self._ui.cancelCalculation.setVisible(status != SolverStatus.NONE)
        self._ui.saveAndStopCalculation.setEnabled(status != SolverStatus.NONE)
        self._ui.updateConfiguration.setEnabled(status != SolverStatus.NONE)

