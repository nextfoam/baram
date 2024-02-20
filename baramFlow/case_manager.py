#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from PySide6.QtCore import Signal, QTimer, QObject

from libbaram.utils import rmtree
from libbaram.openfoam.constants import CASE_DIRECTORY_NAME
from libbaram.run import launchSolver, runParallelUtility, STDOUT_FILE_NAME, STDERR_FILE_NAME

from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project
from baramFlow.openfoam import parallel
from baramFlow.openfoam.case_generator import CaseGenerator
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.polymesh.polymesh_loader import PolyMeshLoader
from baramFlow.openfoam.solver import findSolver
from .solver_status import SolverStatus, RunType, SolverProcess
from .coredb.coredb_reader import CoreDBReader

SOLVER_CHECK_INTERVAL = 500
BATCH_DIRECTORY_NAME = 'batch'


class CaseManager(QObject):
    progress = Signal(str)
    caseLoaded = Signal(str)

    def __init__(self):
        super().__init__()

        self._project = Project.instance()

        self._case = None
        self._db = None
        self._solver = None

        self._runType = None
        self._status = None
        self._process = None

        self._monitor = None
        self._generator = None
        self._batchProcess = None
        self._batchStop = False
        self._batchRunning = False

        FileSystem.setCaseRoot(self._livePath())
        self._loadLiveStatus()

    @property
    def name(self):
        return self._case

    @property
    def db(self):
        return self._db

    @property
    def solver(self):
        return self._solver

    async def loadCase(self, name=None, parameters=None, status=SolverStatus.NONE):
        if self._case != name:
            if name is None:
                FileSystem.setCaseRoot(self._livePath())
                self._loadLiveStatus()
                status = None
            else:
                path = self._batchPath(name)
                if not path.is_dir():
                    FileSystem.createBatchCase(path, coredb.CoreDB().getRegions())
                FileSystem.setCaseRoot(path)

            await self._loadVtkMesh()
            self._project.updateCurrentCase(name)

        self.setCase(name, parameters, status)

    def setCase(self, name=None, parameters=None, status=None):
        self._case = name
        self._db = CoreDBReader(parameters)
        self._solver = findSolver(self._db)
        self.caseLoaded.emit(name)
        if status is not None:
            self._setStatus(status)

    def isRunning(self):
        return self._status == SolverStatus.RUNNING

    def isEnded(self):
        return self._status == SolverStatus.ENDED

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
        await self.loadCase()

        await self._generateCase()

        caseRoot = FileSystem.caseRoot()
        process = launchSolver(self._solver, caseRoot, self._project.uuid, parallel.getEnvironment())
        if process:
            self._runType = RunType.PROCESS
            self._setLiveProcess(SolverProcess(process[0], process[1]))
        else:
            raise RuntimeError

    async def initialize(self):
        await self.loadCase()

        await self._initializeCase()

    async def batchRun(self, cases):
        self._batchStop = False
        self._batchRunning = True
        for case, parameters in cases:
            await self.loadCase(case, parameters)

            await self._initializeCase()

            caseRoot = FileSystem.caseRoot()
            stdout = open(caseRoot / STDOUT_FILE_NAME, 'w')
            stderr = open(caseRoot / STDERR_FILE_NAME, 'w')

            self._setStatus(SolverStatus.RUNNING)
            self._batchProcess = await runParallelUtility(self._solver, parallel=parallel.getEnvironment(), cwd=caseRoot,
                                                  stdout=stdout, stderr=stderr)
            result = await self._batchProcess.wait()

            if self._batchStop:
                self._setStatus(SolverStatus.ENDED)
                break

            self._setStatus(SolverStatus.ENDED if result == 1 else SolverStatus.ERROR)

        self._batchProcess = None
        self._batchRunning = False
        self._project.updateSolverStatus(None, SolverStatus.NONE, None)

    def cancel(self):
        if self._generator is not None:
            self._generator.cancel()
            self._generator = None

    def stopBatchRun(self):
        self._batchStop = True

    def clearCases(self, includeMesh=False):
        rmtree(self._batchRoot())

        livePath = self._livePath()
        if includeMesh:
            FileSystem.createCase(livePath)

        FileSystem.setCaseRoot(livePath)
        self.setCase()

    def removeInvalidCases(self, validCases):
        for dir in self._batchRoot().iterdir():
            if dir.name not in validCases:
                rmtree(dir)

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
        self._project.updateSolverStatus(self._case, status, self._process)

    def _setLiveProcess(self, process):
        self._runType = RunType.PROCESS
        self._process = process
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
        FileSystem.initialize()
        await self._generator.setupCase()
        await self._generator.initialize()
        self._generator = None

    async def _loadVtkMesh(self):
        loader = PolyMeshLoader()
        loader.progress.connect(self.progress)

        # Workaround to give some time for QT to set up timer or event loop.
        # This workaround is not necessary on Windows because BARAM for Windows
        #     uses custom-built VTK that is compiled with VTK_ALLOWTHREADS
        await asyncio.sleep(0.1)

        await loader.loadVtk()
