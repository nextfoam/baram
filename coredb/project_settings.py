#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import psutil
from enum import Enum
from filelock import FileLock

import yaml

from coredb.app_settings import AppSettings


SETTINGS_FILE_NAME = 'case.cfg.yaml'
FORMAT_VERSION = 1


class ProjectSettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    CASE_UUID = 'case_uuid'
    CASE_FULL_PATH = 'case_full_path'
    JOB_ID = 'job_id'
    JOB_START_TIME = 'job_start_time'
    PROCESS_ID = 'process_id'
    PROCESS_START_TIME = 'process_start_time'


class ProjectSettings:
    def __init__(self):
        self._settingsDirectory = None
        self._settingsFile = None
        self._settings = {
            ProjectSettingKey.FORMAT_VERSION.value: FORMAT_VERSION,
        }

    @property
    def projectPath(self):
        return self._get(ProjectSettingKey.CASE_FULL_PATH)

    def acquireLock(self, timeout):
        lock = FileLock(os.path.join(self._settingsDirectory, 'case.lock'))
        lock.acquire(timeout=timeout)
        return lock

    def saveAs(self, project):
        self._setPath(project.uuid)
        self._set(ProjectSettingKey.CASE_UUID, project.uuid)
        self._set(ProjectSettingKey.CASE_FULL_PATH, project.directory)
        self._remove(ProjectSettingKey.PROCESS_ID)
        self._remove(ProjectSettingKey.PROCESS_START_TIME)
        self._remove(ProjectSettingKey.JOB_ID)
        self._remove(ProjectSettingKey.JOB_START_TIME)
        os.mkdir(self._settingsDirectory)
        self.save()

    def save(self):
        self._set(ProjectSettingKey.FORMAT_VERSION, FORMAT_VERSION)

        with open(self._settingsFile, 'w') as file:
            yaml.dump(self._settings, file)

    def load(self, uuid_):
        self._setPath(uuid_)

        if os.path.isfile(self._settingsFile):
            with open(self._settingsFile) as file:
                self._settings = yaml.load(file, Loader=yaml.FullLoader)
                return True

        return False

    def setProcess(self, process):
        if process is None:
            self._remove(ProjectSettingKey.PROCESS_ID)
            self._remove(ProjectSettingKey.PROCESS_START_TIME)
        else:
            self._set(ProjectSettingKey.PROCESS_ID, process[0])
            self._set(ProjectSettingKey.PROCESS_START_TIME, process[1])

        self.save()

    def getProcess(self):
        pid = self._get(ProjectSettingKey.PROCESS_ID)
        startTime = self._get(ProjectSettingKey.PROCESS_START_TIME)

        if pid and startTime:
            try:
                ps = psutil.Process(pid=int(pid))
                if ps.create_time() == float(startTime):
                    return int(pid), float(startTime)
            except psutil.NoSuchProcess:
                pass

            self.setProcess(None)
        return None

    def setJob(self, jobKey):
        self._set(ProjectSettingKey.JOB_ID, jobKey[0])
        self._set(ProjectSettingKey.JOB_START_TIME, jobKey[1])
        self.save()

    def getJob(self):
        return self._get(ProjectSettingKey.JOB_ID.value), self._get(ProjectSettingKey.JOB_START_TIME)

    def _setPath(self, uuid_):
        self._settingsDirectory = os.path.join(AppSettings.casesDirectory(), uuid_)
        self._settingsFile = os.path.join(self._settingsDirectory, SETTINGS_FILE_NAME)

    def _get(self, key):
        if self._settings:
            return self._settings[key.value] if key.value in self._settings else None

        return None

    def _set(self, key, value):
        self._settings[key.value] = value

    def _remove(self, key):
        self._settings.pop(key.value, None)
