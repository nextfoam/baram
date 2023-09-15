#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
from filelock import FileLock

import yaml

from baram.coredb.app_settings import AppSettings


SETTINGS_FILE_NAME = 'case.cfg.yaml'
FORMAT_VERSION = 1


class ProjectSettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    UUID = 'case_uuid'
    PATH = 'case_full_path'
    JOB_ID = 'job_id'
    JOB_START_TIME = 'job_start_time'
    PROCESS_ID = 'process_id'
    PROCESS_START_TIME = 'process_start_time'


class ProjectSettings:
    def __init__(self):
        self._settingsPath = None
        self._settingsFile = None
        self._settings = {
            ProjectSettingKey.FORMAT_VERSION.value: FORMAT_VERSION,
        }

    @property
    def path(self):
        return self.get(ProjectSettingKey.PATH)

    def get(self, key):
        if self._settings:
            return self._settings[key.value] if key.value in self._settings else None

        return None

    def setProcess(self, process):
        if process:
            self._set(ProjectSettingKey.PROCESS_ID, process[0])
            self._set(ProjectSettingKey.PROCESS_START_TIME, process[1])
        else:
            self._remove(ProjectSettingKey.PROCESS_ID)
            self._remove(ProjectSettingKey.PROCESS_START_TIME)

        self.save()

    def getProcess(self):
        return self.get(ProjectSettingKey.PROCESS_ID), self.get(ProjectSettingKey.PROCESS_START_TIME)

    def acquireLock(self, timeout):
        lock = FileLock(self._settingsPath / 'case.lock')
        lock.acquire(timeout=timeout)
        return lock

    def saveAs(self, project):
        self._setPath(project.uuid, True)
        self._set(ProjectSettingKey.UUID, project.uuid)
        self._set(ProjectSettingKey.PATH, str(project.path))
        self._remove(ProjectSettingKey.PROCESS_ID)
        self._remove(ProjectSettingKey.PROCESS_START_TIME)
        self._remove(ProjectSettingKey.JOB_ID)
        self._remove(ProjectSettingKey.JOB_START_TIME)
        self.save()

    def save(self):
        self._set(ProjectSettingKey.FORMAT_VERSION, FORMAT_VERSION)

        with open(self._settingsFile, 'w') as file:
            yaml.dump(self._settings, file)

    def load(self, uuid_):
        self._setPath(uuid_)

        if self._settingsFile.is_file():
            with open(self._settingsFile) as file:
                self._settings = yaml.load(file, Loader=yaml.FullLoader)
                return True

        return False

    def _setPath(self, uuid_, create=False):
        self._settingsPath = AppSettings.casesPath() / uuid_
        self._settingsFile = self._settingsPath / SETTINGS_FILE_NAME
        if create:
            self._settingsPath.mkdir(exist_ok=True)

    def _set(self, key, value):
        self._settings[key.value] = value

    def _remove(self, key):
        self._settings.pop(key.value, None)
