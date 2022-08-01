#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import uuid
import psutil
import shutil
from enum import auto, Enum

import yaml
from PySide6.QtCore import QObject, Signal, QTimer
from pathlib import Path

from .project_settings import ProjectSettings, ProjectSettingKey
from .app_settings import AppSettings
from .filedb import FileDB


FORMAT_VERSION = 1
SOLVER_CHECK_INTERVAL = 5000


class SolverStatus(Enum):
    NONE = 0
    WAITING = auto()
    RUNNING = auto()


class RunType(Enum):
    PROCESS = auto()
    JOB = auto()


class _Project(QObject):
    statusChanged = Signal()
    projectChanged = Signal()

    class LocalSettings:
        def __init__(self, directory):
            self._directory = directory
            self._settingsFile = os.path.join(directory, 'baram.cfg')

            self._settings = {}
            self._load()

        def get(self, key):
            if self._settings and key.value in self._settings:
                return self._settings[key.value]

            return None

        def set(self, key, value):
            self._settings[key.value] = value
            self._save()

        def _load(self):
            if os.path.isfile(self._settingsFile):
                with open(self._settingsFile) as file:
                    self._settings = yaml.load(file, Loader=yaml.FullLoader)

            self._settings[ProjectSettingKey.FORMAT_VERSION.value] = FORMAT_VERSION
            self._settings[ProjectSettingKey.CASE_FULL_PATH.value] = self._directory

        def _save(self):
            with open(self._settingsFile, 'w') as file:
                yaml.dump(self._settings, file)

    def __init__(self):
        super().__init__()

        self._meshLoaded = False
        self._status = SolverStatus.NONE

        self._pid = None
        self._pStartTime = None

        self._settings = None

        self._projectSettings = None
        self._projectLock = None

        self._fileDB = None
        self._coreDB = None

    @property
    def uuid(self):
        return self._settings.get(ProjectSettingKey.CASE_UUID)

    @property
    def directory(self):
        return self._settings.get(ProjectSettingKey.CASE_FULL_PATH)

    @property
    def name(self):
        return os.path.basename(self.directory)

    @property
    def runType(self):
        return self._runType

    @property
    def meshLoaded(self):
        return self._meshLoaded

    @property
    def isModified(self):
        return self._fileDB.isModified or self._coreDB.isModified

    @uuid.setter
    def uuid(self, uuid_):
        self._settings.set(ProjectSettingKey.CASE_UUID, uuid_)

    @directory.setter
    def directory(self, directory):
        self._settings.set(ProjectSettingKey.CASE_FULL_PATH, str(Path(directory).resolve()))

    def fileDB(self):
        return self._fileDB

    def coreDB(self):
        return self._coreDB

    def solverProcess(self):
        return self._pid, self._pStartTime

    def solverStatus(self):
        return self._status

    def setMeshLoaded(self):
        self._meshLoaded = True
        self.statusChanged.emit()

    def setSolverJob(self, job):
        pass

    def setSolverProcess(self, process):
        self._projectSettings.setProcess(process)
        self._startProcessMonitor(process)

    def open(self, directory, create=False):
        self._settings = self.LocalSettings(directory)
        self._projectSettings = ProjectSettings()

        self.directory = directory

        if create or self.uuid:
            projectPath = None
            if self.uuid:
                self._projectSettings.load(self.uuid)
                projectPath = self._projectSettings.projectPath

            if not projectPath or (projectPath != self.directory and os.path.isdir(projectPath)):
                # If projectPath is None, the project is just created or copied from somewhere.
                # If projectPath exists but is different from project's directory,
                # the project was copied from projectPath.
                # In both cases above, the project is treated as new.
                # So, save as new project settings with new uuid.
                self.uuid = str(uuid.uuid4())
                self._projectSettings.saveAs(self)
            elif not os.path.isdir(projectPath):
                # projectPath means origin path of the project.
                # And if projectPath is not None and does not exist in file system,
                # then the project has been moved(renamed)
                # So, update project settings with correct projectPath.
                self._projectSettings.save()
        else:
            raise FileNotFoundError

        self._projectLock = self._projectSettings.acquireLock(5)
        AppSettings.updateRecents(self, create)

        self._fileDB = FileDB(self.directory)
        self._coreDB = self._fileDB.load()

        self._meshLoaded = True if self._coreDB.getRegions() else False

        process = self._projectSettings.getProcess()
        if process:
            self._startProcessMonitor(process)
        else:
            self._status = SolverStatus.NONE
            self._pid = None
            self._pStartTime = None

    def close(self):
        self._settings = None
        self._projectLock.release()

    def save(self):
        self._fileDB.save(self._coreDB)

    def saveAs(self, directory):
        shutil.copytree(self.directory, directory, dirs_exist_ok=True)
        self._fileDB.saveAs(self._coreDB, directory)
        self.close()
        self.open(directory, True)
        self.projectChanged.emit()

    def _setStatus(self, status):
        if self._status != status:
            self._status = status
            self.statusChanged.emit()

    def _startProcessMonitor(self, process):
        self._runType = RunType.PROCESS
        self._pid, self._pStartTime = process
        self._updateProcessStatus()

        self._timer = QTimer()
        self._timer.setInterval(SOLVER_CHECK_INTERVAL)
        self._timer.timeout.connect(self._updateProcessStatus)
        self._timer.start()

    def _updateProcessStatus(self):
        try:
            ps = psutil.Process(pid=self._pid)
            if ps.create_time() == self._pStartTime:
                self._setStatus(SolverStatus.RUNNING)
        except psutil.NoSuchProcess:
            self._setStatus(SolverStatus.NONE)
            self._projectSettings.setProcess(None)
            self._timer.stop()

    def _updateJobStatus(self):
        pass


class Project:
    _instance = None

    @classmethod
    def open(cls, directory, create=False):
        assert(cls._instance is None)
        cls._instance = _Project()
        cls._instance.open(directory, create)
        return cls._instance

    @classmethod
    def close(cls):
        if cls._instance:
            cls._instance.close()
        cls._instance = None

    @classmethod
    def instance(cls):
        assert(cls._instance is not None)
        return cls._instance

    @classmethod
    def fileDB(cls):
        return cls.instance().fileDB()

    @classmethod
    def coreDB(cls):
        return cls.instance().coreDB()
