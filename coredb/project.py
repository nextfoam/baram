#!/usr/bin/env python
# -*- coding: utf-8 -*-


import uuid
from enum import auto, Enum
from typing import Optional

import yaml
from PySide6.QtCore import QObject, Signal, QTimer
from pathlib import Path

from openfoam.run import isProcessRunning
from coredb import coredb
from .project_settings import ProjectSettings, ProjectSettingKey
from .app_settings import AppSettings
from .filedb import FileDB


FORMAT_VERSION = 1
SOLVER_CHECK_INTERVAL = 500


class SolverStatus(Enum):
    NONE = 0
    WAITING = auto()
    RUNNING = auto()


class RunType(Enum):
    PROCESS = auto()
    JOB = auto()


class ProjectOpenType(Enum):
    WIZARD = auto()
    SAVE_AS = auto()
    EXISTING = auto()


class _Project(QObject):
    meshStatusChanged = Signal(bool)
    solverStatusChanged = Signal(SolverStatus)
    projectChanged = Signal()

    materialChanged = Signal()

    class LocalSettings:
        def __init__(self, path):
            self._settingsFile = path / 'baram.cfg'

            self._settings = {}
            self._load()

        def get(self, key):
            if self._settings and key.value in self._settings:
                return self._settings[key.value]

            return None

        def set(self, key, value):
            self._settings[key.value] = str(value)
            self._save()

        def _load(self):
            if self._settingsFile.is_file():
                with open(self._settingsFile) as file:
                    self._settings = yaml.load(file, Loader=yaml.FullLoader)

        def _save(self):
            self._settings[ProjectSettingKey.FORMAT_VERSION.value] = FORMAT_VERSION

            with open(self._settingsFile, 'w') as file:
                yaml.dump(self._settings, file)

    def __init__(self):
        super().__init__()

        self._meshLoaded = False
        self._status = SolverStatus.NONE
        self._runType = None

        self._settings = None
        self._projectSettings: Optional[ProjectSettings] = None
        self._projectLock = None

        self._fileDB = None
        self._coreDB = None

        self._timer = None

    @property
    def uuid(self):
        return self._settings.get(ProjectSettingKey.UUID)

    @property
    def path(self):
        return Path(self._settings.get(ProjectSettingKey.PATH))

    @property
    def name(self):
        return self.path.name

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
        self._settings.set(ProjectSettingKey.UUID, uuid_)

    def fileDB(self):
        return self._fileDB

    def solverProcess(self):
        return self._projectSettings.get(ProjectSettingKey.PROCESS_ID),\
               self._projectSettings.get(ProjectSettingKey.PROCESS_START_TIME)

    def solverStatus(self):
        return self._status

    def setMeshLoaded(self, loaded):
        self._meshLoaded = loaded
        self.meshStatusChanged.emit(loaded)

    def setSolverProcess(self, process):
        self._runType = RunType.PROCESS
        self._projectSettings.setProcess(process)
        if self._updateProcessStatus() != SolverStatus.NONE:
            self._startProcessMonitor(process)

    def save(self):
        self._fileDB.save()

    def saveAs(self, directory):
        self._fileDB.saveAs(directory)
        self._close()
        self._open(directory, ProjectOpenType.SAVE_AS)
        self.projectChanged.emit()

    def _open(self, directory, route=ProjectOpenType.EXISTING):
        path = Path(directory).resolve()

        self._settings = self.LocalSettings(path)
        self._projectSettings = ProjectSettings()

        self._settings.set(ProjectSettingKey.PATH, path)

        if route != ProjectOpenType.EXISTING or self.uuid:
            projectPath = None
            if self.uuid and self._projectSettings.load(self.uuid):
                projectPath = Path(self._projectSettings.path)

            if not projectPath or (projectPath != self.path and projectPath.is_dir()):
                # If projectPath is None, the project is just created or copied from somewhere.
                # If projectPath exists but is different from project's directory,
                # the project was copied from projectPath.
                # In both cases above, the project is treated as new.
                # So, save as new project settings with new uuid.
                self.uuid = str(uuid.uuid4())
                self._projectSettings.saveAs(self)
            elif not projectPath.is_dir():
                # projectPath means origin path of the project.
                # And if projectPath is not None and does not exist in file system,
                # then the project has been moved(renamed)
                # So, update project settings with correct projectPath.
                self._projectSettings.save()
        else:
            raise FileNotFoundError

        self._projectLock = self._projectSettings.acquireLock(0.01)
        AppSettings.updateRecents(self, route != ProjectOpenType.EXISTING)

        self._fileDB = FileDB(self.path)
        if route == ProjectOpenType.WIZARD:
            # CoreDB should have been created by the wizard,
            # Save that configurations as new project.
            self._fileDB.saveCoreDB()
            self._coreDB = coredb.CoreDB()
        else:
            self._coreDB = self._fileDB.loadCoreDB()

        self._meshLoaded = True if self._coreDB.getRegions() else False

        process = self._projectSettings.getProcess()
        if process:
            self._runType = RunType.PROCESS
            self._startProcessMonitor(self._projectSettings.getProcess())
        else:
            self._status = SolverStatus.NONE

    def _close(self):
        self._settings = None
        coredb.destroy()
        if self._projectLock:
            self._projectLock.release()

    def _setStatus(self, status):
        if self._status != status:
            self._status = status
            self.solverStatusChanged.emit(status)

    def _startProcessMonitor(self, process):
        self._timer = QTimer()
        self._timer.setInterval(SOLVER_CHECK_INTERVAL)
        self._timer.timeout.connect(self._updateProcessStatus)
        self._timer.start()

    def _updateProcessStatus(self):
        if isProcessRunning(*self.solverProcess()):
            self._setStatus(SolverStatus.RUNNING)
        else:
            self._projectSettings.setProcess(None)
            self._setStatus(SolverStatus.NONE)
            self._runType = None
            self._stopMonitor()

        return self._status

    def _updateJobStatus(self):
        pass

    def _stopMonitor(self):
        if self._timer:
            self._timer.stop()
            self._timer = None


class Project:
    _instance = None

    @classmethod
    def open(cls, directory, openType):
        assert(cls._instance is None)
        cls._instance = _Project()
        cls._instance._open(directory, openType)
        return cls._instance

    @classmethod
    def close(cls):
        if cls._instance:
            cls._instance._close()

        cls._instance = None

    @classmethod
    def instance(cls):
        assert(cls._instance is not None)
        return cls._instance

    @classmethod
    def fileDB(cls):
        return cls.instance().fileDB()
