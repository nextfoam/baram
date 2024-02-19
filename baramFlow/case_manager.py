#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from PySide6.QtCore import Signal, QTimer, QObject

from libbaram import utils
from libbaram.openfoam.constants import CASE_DIRECTORY_NAME
from libbaram.run import launchSolver

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

        FileSystem.setCaseRoot(self._livePath())

        process = self._project.solverProcess()
        if process:
            if process.isRunning():
                self._setLiveProcess(process)
            else:
                self._setStatus(SolverStatus.ENDED)
        else:
            self._setStatus(SolverStatus.NONE)

        self._setCase()

    @property
    def db(self):
        return self._db

    @property
    def solver(self):
        return self._solver

    async def loadCase(self, name=None, parameters=None):
        if self._case != name:
            if name is None:
                FileSystem.setCaseRoot(self._livePath())
            else:
                FileSystem.setCaseRoot(self._batchPath(name))

            caseRoot = FileSystem.caseRoot()
            if not caseRoot.is_dir():
                FileSystem.createCase(caseRoot, True)

            await self._loadVtkMesh()

        self._setCase(name, parameters)
        self.caseLoaded.emit(name)

    def isRunning(self):
        return self._status == SolverStatus.RUNNING

    def isEnded(self):
        return self._status == SolverStatus.ENDED

    def isActive(self):
        return self._status == SolverStatus.WAITING or self._status == SolverStatus.RUNNING

    def status(self):
        return self._status

    def process(self):
        return self._process

    def kill(self):
        self._process.kill()

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

        self._setStatus(SolverStatus.NONE)

        await self._initializeCase()

    def cancel(self):
        if self._generator is not None:
            self._generator.cancel()

    def clearCases(self, includeMesh=False):
        utils.rmtree(self._batchRoot())

        livePath = self._livePath()
        if includeMesh:
            FileSystem.createCase(livePath)

        FileSystem.setCaseRoot(livePath)
        self._setCase()

    def _setCase(self, name=None, parameters=None):
        self._case = name
        self._db = CoreDBReader(parameters)
        self._solver = findSolver(self._db)

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
        self._status = None
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
