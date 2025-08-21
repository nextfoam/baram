#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock

from PySide6.QtCore import Signal, QTimer, QObject

from baramFlow.base.graphic.graphics_db import GraphicsDB
from baramFlow.openfoam.openfoam_reader import OpenFOAMReader
from libbaram.utils import rmtree
from libbaram.openfoam.constants import CASE_DIRECTORY_NAME
from libbaram.run import launchSolver, runParallelUtility, STDOUT_FILE_NAME, STDERR_FILE_NAME

from .coredb import coredb
from .coredb.project import Project
from .coredb.coredb_reader import CoreDBReader
from .coredb.filedb import FileDB
from .openfoam import parallel
from .openfoam.case_generator import CaseGenerator
from .openfoam.file_system import FileSystem
from .openfoam.solver import findSolver
from .openfoam.system.control_dict import ControlDict
from .solver_status import SolverStatus, RunType, SolverProcess

import shutil # remove later
import os


SOLVER_CHECK_INTERVAL = 500
BATCH_DIRECTORY_NAME = 'batch'
POD_DIRECTORY_NAME = 'pod'

_mutex = Lock()


class Case(QObject):
    progress = Signal(str)

    def __init__(self):
        super().__init__()

        self._name = None
        self._path = None
        self._parameters = None

        self._project = Project.instance()
        self._livePath = self._project.path / CASE_DIRECTORY_NAME

        self._runType = None
        self._status = None

        self._generator = None

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    def status(self):
        return self._status

    def parameters(self):
        return self._parameters

    def isLive(self):
        return self._name is None

    def load(self):
        CoreDBReader().setParameters(self._parameters)
        FileSystem.setCaseRoot(self._path)

    def close(self):
        return

    async def initialize(self):
        if FileSystem.caseRoot() != self._path:
            raise RuntimeError

        self._generator = CaseGenerator()
        self._generator.progress.connect(self.progress)
        self._setStatus(SolverStatus.NONE)
        FileSystem.deleteCalculationResults()
        await self._generator.setupCase()
        await self._generator.initialize()
        self._generator = None

    def cancel(self):
        if self._generator is not None:
            self._generator.cancel()

    def _setStatus(self, status):
        if self._status == status:
            return

        self._status = status
        self._project.updateSolverStatus(self._name, status)

    async def _generateCase(self):
        self._generator = CaseGenerator()
        self._generator.progress.connect(self.progress)
        await self._generator.setupCase()
        self._generator = None


class LiveCase(Case):
    def __init__(self):
        super().__init__()

        self._path = self._livePath

        self._process = None
        self._monitor = None

    def process(self) -> SolverProcess:
        return self._process

    def close(self):
        self._stopMonitor()

    def kill(self):
        if self._process:
            self._process.kill()

    def clear(self):
        self._process = None
        self._status = SolverStatus.NONE
        FileSystem.createCase(self._path)

    async def run(self):
        if FileSystem.caseRoot() != self._path:
            raise RuntimeError

        try:
            await self._generateCase()

            process = launchSolver(findSolver(), self._path, self._project.uuid, parallel.getEnvironment())
            if process:
                self._setProcess(SolverProcess(*process))
            else:
                raise RuntimeError
        except Exception as e:
            self._setStatus(SolverStatus.ERROR)
            raise e

    def loadStatus(self):
        process = self._project.solverProcess()
        if process:
            if process.isRunning():
                self._setProcess(process)
            else:
                self._setStatus(SolverStatus.ENDED)
        elif FileSystem.hasCalculationResults():
            self._setStatus(SolverStatus.ENDED)
        else:
            self._setStatus(SolverStatus.NONE)

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

    def _setProcess(self, process):
        self._runType = RunType.PROCESS
        self._process = process
        self._updateStatus()
        self._startMonitor()

    def _updateStatus(self):
        if self._process.isRunning():
            self._setStatus(SolverStatus.RUNNING)
            self._project.setSolverProcess(self._process)
        else:
            self._setStatus(SolverStatus.ENDED)
            self._stopMonitor()


class BatchCase(Case):
    def __init__(self, name, parameters=None):
        super().__init__()

        self._name = name
        self._path = self._project.path / BATCH_DIRECTORY_NAME / name
        self._parameters = parameters

        self._process = None

        self._status = self._project.getBatchStatus(name)

    def load(self):
        if not self._path.is_dir():
            FileSystem.createBatchCase(self._livePath, self._path, coredb.CoreDB().getRegions())

        super().load()

    async def run(self):
        try:
            if FileSystem.caseRoot() != self._path:
                raise RuntimeError

            await self.initialize()

            stdout = open(self._path / STDOUT_FILE_NAME, 'w')
            stderr = open(self._path / STDERR_FILE_NAME, 'w')

            self._process = await runParallelUtility(findSolver(), parallel=parallel.getEnvironment(), cwd=self._path,
                                                     stdout=stdout, stderr=stderr)
            self._setStatus(SolverStatus.RUNNING)
            returncode = await self._process.wait()
            self._process = None

            self._setStatus(SolverStatus.ENDED if returncode == 0 else SolverStatus.ERROR)
        except Exception as e:
            self._setStatus(SolverStatus.ERROR)
            raise e

    def kill(self):
        if self._process:
            self._process.terminate()


class PODCase(Case):
    def __init__(self):
        super().__init__()

        self._path = self._project.path / POD_DIRECTORY_NAME

        self._process = None

    def process(self) -> SolverProcess:
        return self._process

    def kill(self):
        if self._process:
            self._process.kill()

    async def rmtreePodDirectory(self):
        if self._path.exists(): rmtree(self._path)

    async def initializeGenerateROM(self, listCaseName):
        self._path.mkdir(parents=True, exist_ok=True)

        link_constant = self._path / "constant"
        if not link_constant.exists():
            source = link_constant
            target = self._project.path / "case" / "constant"
            source.symlink_to(os.path.relpath(target, source.parent), target_is_directory=True)

        link_system = self._path / "system"
        if not link_system.exists():
            source = link_system
            target = self._project.path / "case" / "system"
            source.symlink_to(os.path.relpath(target, source.parent), target_is_directory=True)

        # reconstructed case
        case_index = 0
        for caseName in listCaseName:
            snapshotPath = self._project.path / BATCH_DIRECTORY_NAME / caseName
            subfolders = [f for f in snapshotPath.iterdir() if f.is_dir() and f.name.isdigit()]
            if subfolders:
                largest_subfolder = max(subfolders, key=lambda x: int(x.name))
                source = self._path / f"{case_index}"
                target = largest_subfolder
                if not source.exists():
                    source.symlink_to(os.path.relpath(target, source.parent), target_is_directory=True)
            case_index += 1
        self.writeFieldList(self._path)

        # decomposed case
        case_index = 0
        constant_link_done = False
        for caseName in listCaseName:
            snapshotPath = self._project.path / BATCH_DIRECTORY_NAME / caseName
            subfoldersProcessor = [f for f in snapshotPath.iterdir() if f.is_dir() and "processor" in f.name]
            for pProc in subfoldersProcessor:
                processorPath = pProc
                proc_dir = self._path / pProc.name

                # polyMesh (최초 1회만)
                if not constant_link_done:
                    proc_dir.mkdir(parents=True, exist_ok=True)
                    source = proc_dir / "constant"
                    target = processorPath / "constant"
                    if not source.exists():
                        source.symlink_to(os.path.relpath(target, source.parent), target_is_directory=True)

                # time
                subfolders = [f for f in processorPath.iterdir() if f.is_dir() and f.name.isdigit()]
                if subfolders:
                    largest_subfolder = max(subfolders, key=lambda x: int(x.name))
                    proc_dir.mkdir(parents=True, exist_ok=True)
                    source = proc_dir / f"{case_index}"
                    target = largest_subfolder
                    if not source.exists():
                        source.symlink_to(os.path.relpath(target, source.parent), target_is_directory=True)
                    self.writeFieldList(proc_dir)
            case_index += 1
            constant_link_done = True

    async def initializeReconstruct(self, listSnapshot, paramsToReconstruct):
        with open(str(self._project.path) + "/%s/Vinput.dat"%POD_DIRECTORY_NAME, 'w') as f:
            f.write("%d %d\n"%(len(listSnapshot), len(paramsToReconstruct)))
            for _, case in listSnapshot.items():
                f.write("%s\n"%(" ".join(list(case.values()))))

        with open(str(self._project.path) + "/%s/CurrentInput.dat"%POD_DIRECTORY_NAME, 'w') as f:
            f.write("1 %d\n"%len(paramsToReconstruct))
            f.write("%s\n"%(" ".join(list(map(str, paramsToReconstruct)))))

    async def runGenerateROM(self, listCaseName):
        try:
            await self.rmtreePodDirectory()
            await self.initializeGenerateROM(listCaseName)

            stdout = open(self._path / STDOUT_FILE_NAME, 'w')
            stderr = open(self._path / STDERR_FILE_NAME, 'w')

            self._process = await runParallelUtility('baramPODbuildROM', parallel=parallel.getEnvironment(), cwd=self._path,
                                                     stdout=stdout, stderr=stderr)
            self._setStatus(SolverStatus.RUNNING)
            result = await self._process.wait()
            self._process = None

            self._setStatus(SolverStatus.ENDED if result == 0 else SolverStatus.ERROR)
        except Exception as e:
            self._setStatus(SolverStatus.ERROR)
            raise e

    async def runReconstruct(self, listSnapshot, paramsToReconstruct):
        try:
            await self.initializeReconstruct(listSnapshot, paramsToReconstruct)

            stdout = open(self._path / STDOUT_FILE_NAME, 'w')
            stderr = open(self._path / STDERR_FILE_NAME, 'w')

            self._process = await runParallelUtility('baramPODreconstruct', parallel=parallel.getEnvironment(), cwd=self._path,
                                                     stdout=stdout, stderr=stderr)
            self._setStatus(SolverStatus.RUNNING)
            result = await self._process.wait()
            self._process = None

            if result == 0:
                self._setStatus(SolverStatus.ENDED)
            else:
                self._setStatus(SolverStatus.ERROR)
        except Exception as e:
            self._setStatus(SolverStatus.ERROR)
            raise e

    def getROMAccuracy(self):
        constant_dir = self._project.path / POD_DIRECTORY_NAME / "constant"
        filesEigenvalue = [f for f in constant_dir.iterdir() if f.is_file() and f.name.startswith("EigenValues_") and f.name.endswith(".dat")]

        ratios = []

        for file in filesEigenvalue:
            with file.open("r") as f:
                lines = [float(line.strip()) for line in f if line.strip()]
                if not lines: continue
                eps = 1.e-16
                maxEigenvalue = lines[0]
                minEigenvalue = next((val for val in reversed(lines) if abs(val) > eps), eps)
                ratio = abs(maxEigenvalue / minEigenvalue)
                ratios.append(ratio)

        return sum(ratios) / len(ratios)

    def writeFieldList(self, fieldPath):
        with open(str(fieldPath / "listField.dat"), 'w') as f:
            for field in [["U", "vector"], ["p", "scalar"]]:
                f.write("%s\n"%(" ".join(field)))

    def saveToBatchCase(self, caseName):
        dir_pod = self._project.path / POD_DIRECTORY_NAME
        dir_batch = self._project.path / BATCH_DIRECTORY_NAME / caseName

        # reconstructed case
        dir_reconstructed_pod = dir_pod / "10001"
        if dir_reconstructed_pod.exists():
            dir_reconstructed_batch = dir_batch / "1"
            if dir_reconstructed_batch.exists(): rmtree(dir_reconstructed_batch)
            shutil.copytree(dir_reconstructed_pod, dir_reconstructed_batch)

        # decomposed case
        dir_processor_pod = [f for f in dir_pod.iterdir() if f.is_dir() and "processor" in f.name]
        for pProc in dir_processor_pod:
            dir_processor_batch = dir_batch / pProc.name
            if not dir_processor_batch.exists():
                dir_processor_batch.mkdir(parents=True, exist_ok=True)

            dir_reconstructed_pod = pProc / "10001"
            if dir_reconstructed_pod.exists():
                dir_reconstructed_batch = dir_processor_batch / "1"
                if dir_reconstructed_batch.exists(): rmtree(dir_reconstructed_batch)
                shutil.copytree(dir_reconstructed_pod, dir_reconstructed_batch)


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

        self._liveCase = None
        self._currentCase: Case = None

        self._generator = None
        self._batchProcess = None
        self._batchRunning = False
        self._batchStop = False

    def currentCaseName(self):
        return self._caseName

    def liveCase(self):
        return self._liveCase

    def load(self, liveCase: LiveCase):
        self._project = Project.instance()
        self._liveCase = liveCase
        liveCase.load()
        liveCase.loadStatus()
        liveCase.progress.connect(self.progress)
        self._setCurrentCase(liveCase)

    def clear(self):
        if self._liveCase:
            self._liveCase.close()

        self._project = None
        self._caseName = None

    async def loadLiveCase(self):
        if not self._currentCase.isLive():
            self._loadCase(self._liveCase)

            async with OpenFOAMReader() as reader:
                await reader.setupReader()

            await GraphicsDB().updatePolyMeshAll()

        return self._currentCase

    def loadBatchCase(self, case):
        if self._currentCase.name != case.name:
            self._loadCase(case)
            # "OpenFOAMReader.setupReader" and "ScaffoldDB().refreshAllScaffolds" in "loadLiveCase"
            # is handled in a function calling "loadBatchCase" because of "batchRun".
            # We don't need to update Graphics reports whenever a batch case is loaded during batchRun.

        return self._currentCase

    def isRunning(self):
        return self._currentCase.status() == SolverStatus.RUNNING

    def isEnded(self):
        return self._currentCase.status() == SolverStatus.ENDED or self._currentCase.status() == SolverStatus.ERROR

    def isActive(self):
        return self._currentCase.status() == SolverStatus.WAITING or self._currentCase.status() == SolverStatus.RUNNING

    def status(self):
        return self._currentCase.status()

    def isBatchRunning(self):
        return self._batchRunning and self.isRunning()

    def liveProcess(self):
        return self._liveCase.process()

    async def liveRun(self):
        case = await self.loadLiveCase()
        await case.run()

    async def batchRun(self, cases):
        self._batchStop = False
        self._batchRunning = True
        for case in cases:
            await self.loadBatchCase(case).run()

            if self._batchStop:
                break

        self._batchRunning = False

        async with OpenFOAMReader() as reader:
            await reader.setupReader()

        await GraphicsDB().updatePolyMeshAll()

    async def podRunGenerateROM(self, listCaseName):
        tempPodCase = PODCase()
        tempPodCase.load()
        self._setCurrentCase(tempPodCase)
        await tempPodCase.runGenerateROM(listCaseName)

    async def podRunReconstruct(self, listSnapshot, paramsToReconstruct):
        tempPodCase = PODCase()
        tempPodCase.load()
        self._setCurrentCase(tempPodCase)
        await tempPodCase.runReconstruct(listSnapshot, paramsToReconstruct.values())

    async def podSaveToBatchCase(self, caseName, paramsToReconstruct):
        caseToReconstruct = BatchCase(caseName, paramsToReconstruct)
        caseToReconstruct.load()

        tempPodCase = PODCase()
        tempPodCase.load()
        self._setCurrentCase(tempPodCase)
        tempPodCase.saveToBatchCase(caseName)
		
    async def podAddToBatchList(self, caseName, paramsToReconstruct):
        batchStatuses = self._project.loadBatchStatuses()
        batchStatuses[caseName] = 'ENDED'
        batchDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
        batchDataFrame.loc[caseName] = {key: str(value) for key, value in paramsToReconstruct.items()}

        self._project.updateBatchStatuses(batchStatuses)
        self._project.setBatchStatus(caseName, SolverStatus.ENDED)
        self._project.fileDB().putDataFrame(FileDB.Key.BATCH_CASES.value, batchDataFrame)

    def podGetROMAccuracy(self):
        tempPodCase = PODCase()
        self._setCurrentCase(tempPodCase)
        return tempPodCase.getROMAccuracy()

    async def initialize(self):
        case = await self.loadLiveCase()
        await case.initialize()

    def saveAndStop(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'writeNow'
        controlDict.writeAtomic()

    def kill(self):
        if self._currentCase:
            self._currentCase.kill()

    def cancel(self):
        if self._currentCase:
            self._currentCase.cancel()

    def stopBatchRun(self):
        self._batchStop = True
        self.cancel()

    def clearCases(self):
        # rmtree(self._batchRoot())

        self._liveCase.clear()
        self._liveCase.load()

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

    def _setCurrentCase(self, case):
        self._currentCase = case
        self.caseLoaded.emit(case.name)

    def _batchRoot(self):
        return self._project.path / BATCH_DIRECTORY_NAME

    def _batchPath(self, name):
        return self._batchRoot() / name

    def _loadCase(self, case: Case):
        self._currentCase.close()
        case.load()
        self._setCurrentCase(case)
