#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
from pathlib import Path

import yaml
from filelock import FileLock

from libbaram.mpi import ParallelEnvironment, ParallelType

from baramMesh.settings.app_settings import appSettings


FORMAT_VERSION = 1
FILE_NAME = 'local.cfg'


class LocalSettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    PATH = 'case_full_path'
    PARALLEL_NP = 'parallel_np'
    PARALLEL_TYPE = 'parallel_type'
    PARALLEL_HOSTS = 'parallel_hosts'


class LocalSettings:
    def __init__(self, path):
        self._settingsFile = path / FILE_NAME

        self._settings = None
        self._lock = None

        self._load()
        if self._settings is None:
            self._create()

        self.set(LocalSettingKey.PATH, str(path.resolve()))

    @property
    def path(self):
        if path := self.get(LocalSettingKey.PATH):
            return Path(path)

        return None

    def parallelEnvironment(self):
        type_ = self.get(LocalSettingKey.PARALLEL_TYPE)

        return ParallelEnvironment(
            self.get(LocalSettingKey.PARALLEL_NP, 1),
            ParallelType.LOCAL_MACHINE if type_ is None else ParallelType[type_],
            self.get(LocalSettingKey.PARALLEL_HOSTS, '')
        )

    def setParallelEnvironment(self, environment):
        self.set(LocalSettingKey.PARALLEL_NP, environment.np()),
        self.set(LocalSettingKey.PARALLEL_TYPE, environment.type().name),
        self.set(LocalSettingKey.PARALLEL_HOSTS, environment.hosts())

    def acquireLock(self, timeout):
        self._lock = FileLock(self.path / 'case.lock')
        self._lock.acquire(timeout=timeout)

    def releaseLock(self):
        self._lock.release()

    def get(self, key, default=None):
        return self._settings.get(key.value, default)

    def set(self, key, value):
        if self.get(key) != value:
            self._settings[key.value] = value
            self._save()

    def saveAs(self, path):
        self._settings[LocalSettingKey.FORMAT_VERSION.value] = FORMAT_VERSION
        self._settings[LocalSettingKey.PATH.value] = str(path.resolve())

        with open(path / FILE_NAME, 'w') as file:
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
                self._save()
        # End

    def _create(self):
        environment = appSettings.getParallenEnvironment()
        
        self._settings = {
            LocalSettingKey.PARALLEL_NP.value:      environment.np(),
            LocalSettingKey.PARALLEL_TYPE.value:    environment.type().name,
            LocalSettingKey.PARALLEL_HOSTS.value:   environment.hosts()
        }

    def _save(self):
        self._settings[LocalSettingKey.FORMAT_VERSION.value] = FORMAT_VERSION

        with open(self._settingsFile, 'w') as file:
            yaml.dump(self._settings, file)
