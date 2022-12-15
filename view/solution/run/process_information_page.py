#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psutil
import signal
import time
import platform
import qasync
import asyncio
import logging
import shutil

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


logger = logging.getLogger(__name__)

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
        return True

    def _connectSignalsSlots(self):
        self._ui.startCalculation.clicked.connect(self._startCalculationClicked)
        self._ui.cancelCalculation.clicked.connect(self._cancelCalculationClicked)
        self._ui.saveAndStopCalculation.clicked.connect(self._saveAndStopCalculationClicked)
        self._ui.updateConfiguration.clicked.connect(self._updateConfigurationClicked)
        self._project.solverStatusChanged.connect(self._updateStatus)

    @qasync.asyncSlot()
    async def _startCalculationClicked(self):
        caseRoot = FileSystem.caseRoot()

        numCores = int(self._db.getValue('.//runCalculation/parallel/numberOfCores'))
        processorFolders = list(caseRoot.glob('processor[0-9]*'))
        nProcessorFolders = len(processorFolders)
        solvers = openfoam.solver.findSolvers()

        progress = ProgressDialog(self, self.tr('Calculation Run.'), self.tr('Generating case'))

        try:
            # Reconstruct the case if necessary.
            if nProcessorFolders > 0 and nProcessorFolders != numCores:
                proc = await runUtility('reconstructPar', '-allRegions', '-newTimes', '-case', caseRoot, cwd=caseRoot)
                progress.setProcess(proc, self.tr('Reconstructing the case.'))
                result = await proc.wait()
                if progress.canceled():
                    return
                elif result:
                    progress.error(self.tr('Reconstruction failed.'))
                    return
                nProcessorFolders = 0

                for folder in processorFolders:
                    shutil.rmtree(folder)

            # Generate dictionary files
            caseGenerator = CaseGenerator()
            result = await asyncio.to_thread(caseGenerator.generateFiles)
            if not result:
                progress.error(self.tr('Case generating fail. - ' + caseGenerator.getErrors()))
                return

            # Decompose the case if necessary.
            if numCores > 1 and nProcessorFolders == 0:
                proc = await runUtility('decomposePar', '-allRegions', '-case', caseRoot, cwd=caseRoot)

                progress.setProcess(proc, self.tr('Decomposing the case.'))
                result = await proc.wait()
                if progress.canceled():
                    return
                elif result:
                    progress.error(self.tr('Decomposing failed.'))
                    return

            progress.close()
        except Exception as ex:
            logger.info(ex, exc_info=True)
            progress.error(self.tr('Error occurred:\n' + str(ex)))

        process = launchSolver(solvers[0], caseRoot, self._project.uuid, numCores)
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
