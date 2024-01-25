#!/usr/bin/env python
# -*- coding: utf-8 -*-
import psutil
import time
import qasync
import logging
from enum import Enum, auto

from PySide6.QtWidgets import QMessageBox

from libbaram.run import launchSolver
from widgets.list_table import ListItem
from widgets.progress_dialog import ProgressDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project, SolverStatus
from baramFlow.openfoam import parallel
from baramFlow.openfoam.case_generator import CaseGenerator
from baramFlow.openfoam.system.fv_solution import FvSolution
from baramFlow.openfoam.system.control_dict import ControlDict
from baramFlow.openfoam.system.fv_schemes import FvSchemes
import baramFlow.openfoam.solver
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.view.widgets.content_page import ContentPage
from .process_information_page_ui import Ui_ProcessInformationPage
from .user_parameters_dialog import UserParametersDialog


logger = logging.getLogger(__name__)

SOLVER_CHECK_INTERVAL = 3000


class RunningMode(Enum):
    LIVE_RUNNING_MODE = auto()
    BATCH_RUNNING_MODE = auto()


class ProcessInformationPage(ContentPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ProcessInformationPage()
        self._ui.setupUi(self)

        self._project = Project.instance()

        self._stopDialog = None
        self._runningMode = None

        self._dialog = None

        self._connectSignalsSlots()

        self._setRunningMode(RunningMode.LIVE_RUNNING_MODE)
        self._updateUserParameters()

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _load(self):
        self._updateStatus()

    def _connectSignalsSlots(self):
        self._ui.startCalculation.clicked.connect(self._startCalculationClicked)
        self._ui.cancelCalculation.clicked.connect(self._cancelCalculationClicked)
        self._ui.saveAndStopCalculation.clicked.connect(self._saveAndStopCalculationClicked)
        self._ui.updateConfiguration.clicked.connect(self._updateConfigurationClicked)
        self._ui.userParametersGroup.toggled.connect(self._toggleUserParameters)
        self._ui.editUserParametrer.clicked.connect(self._editUserParameters)
        self._project.solverStatusChanged.connect(self._updateStatus)

    def _setRunningMode(self, mode):
        if mode == RunningMode.LIVE_RUNNING_MODE:
            self._ui.updateConfiguration.show()
            self._ui.batchCases.hide()
            self._ui.toBatchMode.show()
            self._ui.toLiveMode.hide()
        else:
            self._ui.updateConfiguration.hide()
            self._ui.batchCases.show()
            self._ui.toBatchMode.hide()
            self._ui.toLiveMode.sbow()

        self._runningMode = mode

    @qasync.asyncSlot()
    async def _startCalculationClicked(self):
        progressDialog = ProgressDialog(self, self.tr('Calculation Run.'), True)

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

        caseRoot = FileSystem.caseRoot()
        solvers = baramFlow.openfoam.solver.findSolvers()

        process = launchSolver(solvers[0], caseRoot, self._project.uuid, parallel.getEnvironment())
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
        self._stopDialog = ProgressDialog(self, self.tr('Calculation Canceling'))
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
        regions = coredb.CoreDB().getRegions()
        for rname in regions:
            FvSchemes(rname).build().write()
            FvSolution(rname).build().write()
        ControlDict().build().writeAtomic()

    def _toggleUserParameters(self, checked):
        self._ui.userParameters.setVisible(checked)

    def _editUserParameters(self):
        self._dialog = UserParametersDialog(self)
        self._dialog.accepted.connect(self._updateUserParameters)
        self._dialog.open()

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

    def _updateUserParameters(self):
        parameters = coredb.CoreDB().getBatchParameters()

        self._ui.userParameterList.clear()
        for name, data in parameters.items():
            self._ui.userParameterList.addItem(ListItem(name, [f'{name}({len(data["usages"])})', data['value']]))
