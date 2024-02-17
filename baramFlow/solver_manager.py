#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal, QTimer, QObject

from libbaram.run import launchSolver

from baramFlow.coredb.project import Project
from baramFlow.openfoam import parallel
from baramFlow.openfoam.case_generator import CaseGenerator
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver import findSolver
from .solver_status import SolverStatus, RunType, SolverProcess


SOLVER_CHECK_INTERVAL = 500


class Case(QObject):
    progress = Signal(str)

    def __init__(self, name=None, path=None):
        super().__init__()
        self._name = None
        self._generator = None

        if name:
            FileSystem.switchToBatchCase(path)
        else:
            FileSystem.switchToLiveCase()

    @property
    def name(self):
        return self._name

    async def generate(self):
        self._generator = CaseGenerator()
        self._generator.progress.connect(self.progress)
        await self._generator.setupCase()
        self._generator = None

    async def initialize(self):
        self._generator = CaseGenerator()
        self._generator.progress.connect(self.progress)
        await self._generator.setupCase()
        await self._generator.initialize()
        self._generator = None

    def cancel(self):
        if self._generator is not None:
            self._generator.cancel()


class SolverManager(QObject):
    progress = Signal(str)

    def __init__(self):
        super().__init__()

        self._case = None
        self._runType = None
        self._status = None
        self._process = None
        self._solver = None
        self._monitor = None
        self._project = Project.instance()

        FileSystem.setupForProject()
        self.setCase()

        process = self._project.solverProcess()
        if process:
            if process.isRunning():
                self._setProcess(process)
            else:
                self._setStatus(SolverStatus.ENDED)
        else:
            self._setStatus(SolverStatus.NONE)

    def setCase(self, name=None, path=None, status=None):
        self._case = Case(name, path)
        self._status = status
        self._case.progress.connect(self.progress)

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

    async def liveRun(self, uuid):
        self._solver = findSolver()
        await self._case.generate()

        caseRoot = FileSystem.caseRoot()
        process = launchSolver(self._solver, caseRoot, uuid, parallel.getEnvironment())
        if process:
            self._setProcess(SolverProcess(process[0], process[1]))
        else:
            raise RuntimeError

        self._runType = RunType.PROCESS

    async def initialize(self):
        self._solver = findSolver()
        await FileSystem.initialize()
        self._setStatus(SolverStatus.NONE)
        await self._case.initialize()

    def cancelLiveRun(self):
        self._case.cancel()

    def cancelInitilization(self):
        self._case.cancel()

    def _setStatus(self, status):
        if self._status == status:
            return

        self._status = status
        self._project.updateSolverStatus(self._case.name, status, self._process)

    def _setProcess(self, process):
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
