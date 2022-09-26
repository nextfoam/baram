#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import psutil
import signal
import time
import platform
import qasync
import asyncio

from PySide6.QtWidgets import QWidget, QMessageBox

from coredb import coredb
from coredb.project import Project, SolverStatus
from openfoam.run import launchSolver, runUtility
from openfoam.case_generator import CaseGenerator
from openfoam.system.fv_solution import FvSolution
from openfoam.system.control_dict import ControlDict
from openfoam.system.fv_schemes import FvSchemes
import openfoam.solver
from openfoam.file_system import FileSystem
from view.widgets.progress_dialog import ProgressDialog
from .process_information_page_ui import Ui_ProcessInformationPage

SOLVER_CHECK_INTERVAL = 3000


class ProcessInformationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ProcessInformationPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._project = Project.instance()

        self._stopDialog = None

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
        self._project.solverStatusChanged.connect(self._updateStatus)

    @qasync.asyncSlot()
    async def _startCalculationClicked(self):
        progress = ProgressDialog(self, self.tr('Calculation Run.'), self.tr('Generating case'))

        caseGenerator = CaseGenerator()
        result = await asyncio.to_thread(caseGenerator.generateFiles)
        if not result:
            progress.error(self.tr('Case generating fail. - ' + caseGenerator.getErrors()))
            return

        controlDict = ControlDict().build()
        controlDict.asDict()['startFrom'] = 'latestTime'
        controlDict.asDict()['stopAt'] = 'endTime'
        controlDict.writeAtomic()

        numCores = self._db.getValue('.//runCalculation/parallel/numberOfCores')

        self._solvers = openfoam.solver.findSolvers()
        self._caseRoot = FileSystem.caseRoot()

        if int(self._db.getValue('.//runCalculation/parallel/numberOfCores')) > 1:
            cwd = FileSystem.caseRoot()
            proc = await runUtility('decomposePar', '-force', '-case', cwd, cwd=cwd)
            progress.setProcess(proc, self.tr('Decomposing the case.'))
            await proc.wait()
            if progress.canceled():
                return

        progress.close()

        print(self._solvers)
        process = launchSolver(self._solvers[0], Path(self._caseRoot), self._project.uuid, int(numCores))
        if process:
            self._project.setSolverProcess(process)
        else:
            QMessageBox.critical(self, self.tr('Calculation Execution Failed'),
                                 self.tr('Solver execution failed or terminated.'))

    def _cancelCalculationClicked(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'noWriteNow'
        controlDict.writeAtomic()

        self._waitingStop()

    def _saveAndStopCalculationClicked(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'writeNow'
        controlDict.writeAtomic()

        self._waitingStop()

    def _waitingStop(self):
        message = self.tr('Waiting for the solver to stop after final calculation. You can "Force Stop",\n'
                          'yet it could corrupt the final iteration result.')
        self._stopDialog = ProgressDialog(self, self.tr('Calculation Canceling'), message)
        self._stopDialog.setButtonToCancel(self._forceStop, self.tr('Force Stop'))

    def _forceStop(self):
        if self._project.solverStatus() == SolverStatus.RUNNING:
            pid, startTime = self._project.solverProcess()
            try:
                ps = psutil.Process(pid)
                with ps.oneshot():
                    if ps.is_running() and ps.create_time() == startTime:
                        if platform.system() == "Windows":
                            ps.send_signal(signal.CTRL_C_EVENT)
                        elif platform.system() == "Linux":
                            ps.send_signal(signal.SIGTERM)
                        else:
                            raise Exception(self.tr('Unsupported OS'))
            except psutil.NoSuchProcess:
                pass

    def _updateConfigurationClicked(self):
        regions = self._db.getRegions()
        for rname in regions:
            FvSchemes(rname).build().write()
            FvSolution(rname).build().write()
        ControlDict().build().writeAtomic()

    def _updateStatus(self):
        status = self._project.solverStatus()

        if status == SolverStatus.NONE:
            text = self.tr('Not Running')
            if self._stopDialog is not None:
                self._stopDialog.close()
                self._stopDialog = None
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

