#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid
from enum import auto, Enum
from typing import Optional

import yaml
from PySide6.QtCore import QObject, Signal
from pathlib import Path

from baramFlow.solver_status import SolverStatus
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_reader import CoreDBReader
from .project_settings import ProjectSettings
from .app_settings import AppSettings
from .filedb import FileDB


FORMAT_VERSION = 1


class ProjectOpenType(Enum):
    NEW = auto()
    SAVE_AS = auto()
    EXISTING = auto()
    MESH = auto()


class SettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    UUID = 'case_uuid'
    PATH = 'case_full_path'
    NP = 'np'
    PARALLEL_TYPE = 'parallel_type'
    HOSTFILE = 'hostfile'
    BATCH_STATUS = 'batch_status'


class _Project(QObject):
    # parameters: solverStatus, batch name, previousStatus
    solverStatusChanged = Signal(SolverStatus, str, SolverStatus)
    projectOpened = Signal()
    projectClosed = Signal()

    materialChanged = Signal()

    class LocalSettings:
        def __init__(self, path, baseSettings):
            self._settingsFile = path / 'local.cfg'

            self._settings = None

            if baseSettings:
                self._settings = baseSettings._settings
                self._settings.pop(SettingKey.UUID.value)
                self._settings.pop(SettingKey.PATH.value)
            else:
                self._load()

        def get(self, key):
            if self._settings and key.value in self._settings:
                return self._settings[key.value]

            return None

        def set(self, key, value):
            if self.get(key) != value:
                self._settings[key.value] = value
                self.save()

        def save(self):
            with open(self._settingsFile, 'w') as file:
                yaml.dump(self._settings, file)

        def _load(self):
            if self._settingsFile.is_file():
                with open(self._settingsFile) as file:
                    self._settings = yaml.load(file, Loader=yaml.FullLoader)
            # ToDo: For compatibility. Remove this code block after 20251231
            # Migration from previous name of "baram.cfg"
            # Begin
            elif (oldFile := self._settingsFile.parent / 'baram.cfg').is_file():
                with open(oldFile) as file:
                    self._settings = yaml.load(file, Loader=yaml.FullLoader)
                    self.save()
            # End
            else:
                self._settings = {}

            self._settings[SettingKey.FORMAT_VERSION.value] = FORMAT_VERSION

    def __init__(self):
        super().__init__()

        self._process = (None, None)
        self._runType = None

        self._settings = None
        self._projectSettings: Optional[ProjectSettings] = None
        self._projectLock = None

        self._fileDB: Optional[FileDB] = None
        self._coreDB = None

        self._timer = None
        self._liveStatus = None

    @property
    def uuid(self) -> str:
        return self._settings.get(SettingKey.UUID)

    @uuid.setter
    def uuid(self, uuid_):
        self._settings.set(SettingKey.UUID, uuid_)

    @property
    def path(self):
        return Path(self._settings.get(SettingKey.PATH))

    @property
    def np(self):
        return self._settings.get(SettingKey.NP)

    @np.setter
    def np(self, np_):
        self._settings.set(SettingKey.NP, np_)

    @property
    def pType(self):
        return self._settings.get(SettingKey.PARALLEL_TYPE)

    @pType.setter
    def pType(self, type_):
        self._settings.set(SettingKey.PARALLEL_TYPE, type_)

    @property
    def hostfile(self):
        return self._settings.get(SettingKey.HOSTFILE)

    @hostfile.setter
    def hostfile(self, hostfile_):
        self._settings.set(SettingKey.HOSTFILE, hostfile_)

    @property
    def name(self):
        return self.path.name

    @property
    def runType(self):
        return self._runType

    @property
    def isModified(self):
        return self._fileDB.isModified or self._coreDB.isModified

    def fileDB(self):
        return self._fileDB

    def getLocalSetting(self, key):
        return self._settings.get(key)

    def setLocalSetting(self, key, value):
        self._settings.set(key, value)

    def solverProcess(self):
        return self._projectSettings.getProcess()

    def setSolverProcess(self, process):
        self._projectSettings.setProcess(process)

    def save(self):
        self._fileDB.save()

    def saveAs(self, directory):
        self._fileDB.saveAs(directory)
        self._close()
        self._open(directory, ProjectOpenType.SAVE_AS)
        self.projectOpened.emit()

    def opened(self):
        self.projectOpened.emit()

    def updateSolverStatus(self, name, status):
        if name:
            self.setBatchStatus(name, status)
            self.solverStatusChanged.emit(status, name, None)

            return

        self.solverStatusChanged.emit(status, None, self._liveStatus)
        self._liveStatus = status

    def loadBatchStatuses(self) -> list[str]:
        status = self._settings.get(SettingKey.BATCH_STATUS)
        if status is None:
            status = {}
            self._settings.set(SettingKey.BATCH_STATUS, status)

        return status

    def updateBatchStatuses(self, statuses: list[str]):
        self._settings.set(SettingKey.BATCH_STATUS, statuses)

    def getBatchStatus(self, name) -> SolverStatus:
        statuses = self._settings.get(SettingKey.BATCH_STATUS)
        if statuses is None:
            return SolverStatus.NONE

        return SolverStatus[statuses[name]] if name in statuses else SolverStatus.NONE

    def setBatchStatus(self, name, status: SolverStatus):
        batches = self.loadBatchStatuses()
        batches[name] = status.name

        self._settings.save()

    def removeBatchStatus(self, name):
        batches = self.loadBatchStatuses()
        if name in batches:
            del batches[name]

        self._settings.save()

    def clearBatchStatuses(self):
        self.updateBatchStatuses({})

    def _open(self, path: Path, route=ProjectOpenType.EXISTING):
        self._settings = self.LocalSettings(path, self._settings)
        if route != ProjectOpenType.SAVE_AS:
            self._projectSettings = ProjectSettings()

        self._settings.set(SettingKey.PATH, str(path))

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
                self._projectSettings.saveAs(self)

            # ToDo: For compatibility. Remove this code block at the appropriate time. (Added on 2025.01.07)
            # Move batch status from Project Settings to Local Settings.
            # Begin
            if not self.loadBatchStatuses():
                if statuses := self._projectSettings.popBatchStatuses():
                    self.updateBatchStatuses(statuses)
                self._projectSettings.save()
            # End
        else:
            raise FileNotFoundError

        self._projectLock = self._projectSettings.acquireLock(0.01)
        AppSettings.updateRecents(self, route != ProjectOpenType.EXISTING)

        self._fileDB = FileDB(self.path)
        if route == ProjectOpenType.NEW or route == ProjectOpenType.MESH:
            # CoreDB should have been created by the wizard,
            # Save that configurations as new project.
            self._fileDB.saveCoreDB()
            self._coreDB = coredb.CoreDB()
        else:
            self._coreDB = self._fileDB.loadCoreDB()

        CoreDBReader().reloadCoreDB()

    def _close(self):
        coredb.destroy()
        self.projectClosed.emit()
        if self._projectLock:
            self._projectLock.release()


class Project:
    _instance: Optional[_Project] = None

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
