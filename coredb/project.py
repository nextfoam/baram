#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import uuid
from enum import auto, Enum

import yaml
import psutil
from PySide6.QtCore import QObject, Signal, QTimer
from pathlib import Path


FORMAT_VERSION = 1
SOLVER_CHECK_INTERVAL = 5000


class SolverStatus(Enum):
    NONE = 0
    WAITING = auto()
    RUNNING = auto()


class ProjectSettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    CASE_UUID = 'case_uuid'
    CASE_FULL_PATH = 'case_full_path'
    JOB_ID = 'job_id'
    JOB_START_TIME = 'job_start_time'
    PROCESS_ID = 'process_id'
    PROCESS_START_TIME = 'process_start_time'


class _Project(QObject):
    statusChanged = Signal(SolverStatus)

    class RunType:
        PROCESS = 0
        JOB = 1

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

        def setJob(self, jobid, startTime):
            self._settings[ProjectSettingKey.JOB_ID.value] = jobid
            self._settings[ProjectSettingKey.JOB_START_TIME.value] = str(startTime)
            self._save()

        def setProcess(self, pid, startTime):
            self._settings[ProjectSettingKey.PROCESS_ID.value] = pid
            self._settings[ProjectSettingKey.PROCESS_START_TIME.value] = str(startTime)
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

    def __init__(self, directory):
        super().__init__()
        self._directory = str(Path(directory).resolve())
        self._settings = self.LocalSettings(directory)
        self._startTime = None
        self._runType = None
        self._status = SolverStatus.NONE
        self._timer = None

    @property
    def uuid(self):
        return self._settings.get(ProjectSettingKey.CASE_UUID)

    @property
    def directory(self):
        return self._directory

    @property
    def name(self):
        return os.path.basename(self._directory)

    @property
    def pid(self):
        return self._settings.get(ProjectSettingKey.PROCESS_ID)

    @property
    def jobid(self):
        return self._settings.get(ProjectSettingKey.JOB_ID)

    def solverStatus(self):
        return self._status

    def renewId(self):
        self._settings.set(ProjectSettingKey.CASE_UUID, str(uuid.uuid4()))

    def setSolverJob(self, jobid, startTime):
        self._startTime = startTime
        self._runType = self.RunType.JOB
        self._settings.setJob(jobid, startTime)
        self._updateJobStatus()
        self._timer = QTimer()
        self._timer.setInterval(SOLVER_CHECK_INTERVAL)
        self._timer.timeout.connect(self._updateJobStatus)
        self._timer.start()

    def setSolverProcess(self, pid, startTime):
        self._startTime = startTime
        self._runType = self.RunType.PROCESS
        self._settings.setProcess(pid, startTime)
        self._updateProcessStatus()
        self._timer = QTimer()
        self._timer.setInterval(SOLVER_CHECK_INTERVAL)
        self._timer.timeout.connect(self._updateProcessStatus)
        self._timer.start()

    def _setStatus(self, status):
        if self._status != status:
            self._status = status
            self.statusChanged.emit(status)

    def _updateProcessStatus(self):
        try:
            ps = psutil.Process(pid=self._settings.get(ProjectSettingKey.PROCESS_ID))
            if ps.create_time() == self._startTime:
                self._setStatus(SolverStatus.RUNNING)
        except psutil.NoSuchProcess:
            self._setStatus(SolverStatus.NONE)
            self._timer.stop()

    def _updateJobStatus(self):
        pass


class Project:
    _currentProject = None

    @classmethod
    def open(cls, directory):
        assert(cls._currentProject is None)
        cls._currentProject = _Project(directory)
        return cls._currentProject

    @classmethod
    def close(cls):
        cls._currentProject = None

    @classmethod
    def instance(cls):
        assert(cls._currentProject is not None)
        return cls._currentProject
