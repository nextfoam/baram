#!/usr/bin/env python
# -*- coding: utf-8 -*-
import psutil
import time
import qasync
import logging

from PySide6.QtWidgets import QMessageBox

from libbaram.run import launchSolver

from baram.coredb import coredb
from baram.coredb.project import Project, SolverStatus
from baram.openfoam import parallel
from baram.openfoam.case_generator import CaseGenerator
from baram.openfoam.system.fv_solution import FvSolution
from baram.openfoam.system.control_dict import ControlDict
from baram.openfoam.system.fv_schemes import FvSchemes
import baram.openfoam.solver
from baram.openfoam.file_system import FileSystem
from baram.view.widgets.content_page import ContentPage
from baram.view.widgets.progress_dialog_simple import ProgressDialogSimple
from .process_information_page_ui import Ui_ProcessInformationPage


logger = logging.getLogger(__name__)

SOLVER_CHECK_INTERVAL = 3000


class ProcessInformationPage(ContentPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ProcessInformationPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._project = Project.instance()

        self._stopDialog = None

        self._connectSignalsSlots()

    def _load(self):
        self._updateStatus()

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.startCalculation.clicked.connect(self._startCalculationClicked)
        self._ui.cancelCalculation.clicked.connect(self._cancelCalculationClicked)
        self._ui.saveAndStopCalculation.clicked.connect(self._saveAndStopCalculationClicked)
        self._ui.updateConfiguration.clicked.connect(self._updateConfigurationClicked)
        self._project.solverStatusChanged.connect(self._updateStatus)

    @qasync.asyncSlot()
    async def _startCalculationClicked(self):
        progressDialog = ProgressDialogSimple(self, self.tr('Calculation Run.'), True)

        caseGenerator = CaseGenerator()
        caseGenerator.progress.connect(progressDialog.setLabelText)

        progressDialog.cancelClicked.connect(caseGenerator.cancel)
        progressDialog.open()

        try:
            cancelled = await caseGenerator.setupCase()
            if cancelled:
                progressDialog.finish(self.tr('Calculation cancelled'))
                return
        except RuntimeError as e:
            progressDialog.finish(self.tr('Case generating fail. - ') + str(e))
            return

        numCores = parallel.getNP()
        caseRoot = FileSystem.caseRoot()
        solvers = baram.openfoam.solver.findSolvers()

        process = launchSolver(solvers[0], caseRoot, self._project.uuid, numCores)
        if process:
            self._project.setSolverProcess(process)
        else:
            QMessageBox.critical(self, self.tr('Calculation Execution Failed'),
                                 self.tr('Solver execution failed or terminated.'))

        progressDialog.finish(self.tr('Calculation started'))

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
        self._stopDialog = ProgressDialogSimple(self, self.tr('Calculation Canceling'))
        self._stopDialog.open()

        self._stopDialog.setLabelText(
            self.tr('Waiting for the solver to stop after final calculation. You can "Force Stop",\n'
                    'yet it could corrupt the final iteration result.'))
        self._stopDialog.showCancelButton(self.tr('Force Stop'))
        self._stopDialog.cancelClicked.connect(self._forceStop)

    def _forceStop(self):
        if self._project.solverStatus() == SolverStatus.RUNNING:
            pid, startTime = self._project.solverProcess()
            try:
                ps = psutil.Process(pid)
                with ps.oneshot():
                    if ps.is_running() and ps.create_time() == startTime:
                        ps.terminate()
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

        if status == SolverStatus.WAITING:
            text = self.tr('Waiting')
        elif status == SolverStatus.RUNNING:
            text = self.tr('Running')
        else:
            text = self.tr('Not Running')
            if self._stopDialog is not None:
                self._stopDialog.close()
                self._stopDialog = None

        pid, startTime = self._project.solverProcess()
        if startTime:
            createTime = time.strftime("%Y-%m-%d, %H:%M:%S", time.localtime(startTime))
        else:
            createTime = '-'

        self._ui.id.setText(str(pid) if pid else '-')
        self._ui.createTime.setText(createTime)
        self._ui.status.setText(text)

        if self._project.isSolverActive():
            self._ui.startCalculation.hide()
            self._ui.cancelCalculation.show()
            self._ui.saveAndStopCalculation.setEnabled(True)
            self._ui.updateConfiguration.setEnabled(True)
        else:
            self._ui.startCalculation.show()
            self._ui.cancelCalculation.hide()
            self._ui.saveAndStopCalculation.setDisabled(True)
            self._ui.updateConfiguration.setDisabled(True)
