#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
from threading import Lock

from PySide6.QtCore import Signal, QTimer, QObject

from libbaram.utils import rmtree
from libbaram.openfoam.constants import CASE_DIRECTORY_NAME
from libbaram.run import launchSolver, runParallelUtility, STDOUT_FILE_NAME, STDERR_FILE_NAME

from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project
from baramFlow.openfoam import parallel
from baramFlow.openfoam.case_generator import CaseGenerator
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver import findSolver
from .openfoam.system.control_dict import ControlDict
from .solver_status import SolverStatus, RunType, SolverProcess
from .coredb.coredb_reader import CoreDBReader


SOLVER_CHECK_INTERVAL = 500
BATCH_DIRECTORY_NAME = 'batch'

_mutex = Lock()


class CaseManager(QObject):
    progress = Signal(str)
    caseLoaded = Signal(str)
    caseCleared = Signal()
    batchCleared = Signal()

    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(CaseManager, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        with _mutex:
            if hasattr(self, '_initialized'):
                return
            else:
                self._initialized = True

        super().__init__()

        self._project = None
        self._caseName = None

        self._runType = None
        self._status = None
        self._process = None

        self._monitor = None
        self._generator = None
        self._batchProcess = None
        self._batchRunning = False

    @property
    def name(self):
        return self._caseName

    def load(self):
        self._project = Project.instance()
        self.loadLiveCase(True)

    def clear(self):
        self._stopMonitor()

        self._project = None
        self._caseName = None

        self._runType = None
        self._status = None

    def loadLiveCase(self, projectLoaded=False):
        if self._caseName is None and not projectLoaded:  # it's already Live Case
            return

        self.setCase(None, self._livePath(), None)
        self._loadLiveStatus()

    def loadBatchCase(self, name, parameters, status=SolverStatus.NONE):
        if self._caseName == name:  # same case
            return

        CoreDBReader().setParameters(parameters)

        path = self._batchPath(name)
        if not path.is_dir():
            FileSystem.createBatchCase(self._livePath(), path, coredb.CoreDB().getRegions())
        self.setCase(name, path, status)

    def setCase(self, name, path: Path, status=None):
        self._caseName = name
        FileSystem.setCaseRoot(path)
        self.caseLoaded.emit(name)
        if status is not None:
            self._setStatus(status)

    def isRunning(self):
        return self._status == SolverStatus.RUNNING

    def isEnded(self):
        return self._status == SolverStatus.ENDED or self._status == SolverStatus.ERROR

    def isActive(self):
        return self._status == SolverStatus.WAITING or self._status == SolverStatus.RUNNING

    def status(self):
        return self._status

    def isBatchRunning(self):
        return self._batchRunning

    def process(self):
        return self._process

    def kill(self):
        self.stopBatchRun()

        if self._process:
            self._process.kill()

        if self._batchProcess:
            self._batchProcess.terminate()

    async def liveRun(self):
        self.loadLiveCase()

        await self._generateCase()

        caseRoot = FileSystem.caseRoot()
        solver = findSolver()
        process = launchSolver(solver, caseRoot, self._project.uuid, parallel.getEnvironment())
        if process:
            self._runType = RunType.PROCESS
            self._setLiveProcess(SolverProcess(process[0], process[1]))
        else:
            raise RuntimeError

    async def initialize(self):
        self.loadLiveCase()

        await self._initializeCase()

    async def batchRun(self, cases):
        self._batchStop = False
        self._batchRunning = True
        for case, parameters in cases:
            self.loadBatchCase(case, parameters)

            await self._initializeCase()

            caseRoot = FileSystem.caseRoot()
            stdout = open(caseRoot / STDOUT_FILE_NAME, 'w')
            stderr = open(caseRoot / STDERR_FILE_NAME, 'w')

            solver = findSolver()
            self._batchProcess = await runParallelUtility(solver, parallel=parallel.getEnvironment(), cwd=caseRoot,
                                                          stdout=stdout, stderr=stderr)
            self._setStatus(SolverStatus.RUNNING)
            result = await self._batchProcess.wait()

            if self._batchStop:
                self._setStatus(SolverStatus.ENDED)
                break

            self._setStatus(SolverStatus.ENDED if result == 0 else SolverStatus.ERROR)

        self._batchProcess = None
        self._batchRunning = False
        self._project.updateSolverStatus(None, SolverStatus.ENDED, None)

    def saveAndStop(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'writeNow'
        controlDict.writeAtomic()

    def cancel(self):
        if self._generator is not None:
            self._generator.cancel()
            self._generator = None

    def stopBatchRun(self):
        self._batchStop = True

    def clearCases(self):
        livePath = self._livePath()
        FileSystem.createCase(livePath)
        FileSystem.setCaseRoot(livePath)

        self.caseCleared.emit()
        self._project.clearBatchStatuses()
        self.batchCleared.emit()

    def deleteCalculationResults(self):
        rmtree(self._batchRoot())
        FileSystem.deleteCalculationResults()

        self.caseCleared.emit()
        self._project.clearBatchStatuses()
        self.batchCleared.emit()

    def removeInvalidCases(self, validCases):
        if not self._batchRoot().exists():
            return

        for d in self._batchRoot().iterdir():
            if d.name not in validCases:
                rmtree(d)

    def removeCase(self, name):
        rmtree(self._batchPath(name), ignore_errors=True)

    def _livePath(self):
        return self._project.path / CASE_DIRECTORY_NAME

    def _batchRoot(self):
        return self._project.path / BATCH_DIRECTORY_NAME

    def _batchPath(self, name):
        return self._batchRoot() / name

    def _setStatus(self, status):
        if self._status == status:
            return

        self._status = status
        self._project.updateSolverStatus(self._caseName, status, self._process)

    def _setLiveProcess(self, process):
        self._runType = RunType.PROCESS
        self._process = process
        self._updateStatus()
        self._startMonitor()

    def _startMonitor(self):
        if self._monitor is None:
            self._monitor = QTimer()
            self._monitor.setInterval(SOLVER_CHECK_INTERVAL)
            self._monitor.timeout.connect(self._updateStatus)
            self._monitor.start()

    def _stopMonitor(self):
        if self._monitor:
            self._monitor.stop()
            self._monitor = None
            self._process = None

    def _loadLiveStatus(self):
        process = self._project.solverProcess()
        if process:
            if process.isRunning():
                self._setLiveProcess(process)
            else:
                self._setStatus(SolverStatus.ENDED)
        elif FileSystem.hasCalculationResults():
            self._setStatus(SolverStatus.ENDED)
        else:
            self._setStatus(SolverStatus.NONE)

    def _updateStatus(self):
        if self._process.isRunning():
            self._setStatus(SolverStatus.RUNNING)
        else:
            self._setStatus(SolverStatus.ENDED)
            self._stopMonitor()

    async def _generateCase(self):
        self._generator = CaseGenerator()
        self._generator.progress.connect(self.progress)
        await self._generator.setupCase()
        self._generator = None

    async def _initializeCase(self):
        self._generator = CaseGenerator()
        self._generator.progress.connect(self.progress)
        self._setStatus(SolverStatus.NONE)
        FileSystem.deleteCalculationResults()
        await self._generator.setupCase()
        await self._generator.initialize()
        self._generator = None
