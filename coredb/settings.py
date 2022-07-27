#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
from enum import Enum

import yaml
from filelock import FileLock, Timeout


FORMAT_VERSION = 1
RECENT_CASES_NUMBER = 5


class SettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    DISPLAY_SCALE = 'display_scale'
    RECENT_DIRECTORY = 'recent_directory'
    RECENT_CASES = 'recent_cases'


class Settings:
    _userDirectory = os.path.expanduser('~')
    _settingsDirectory = os.path.join(_userDirectory, '.baram')
    _casesDirectory = os.path.join(_settingsDirectory, 'cases')
    _settingsFile = os.path.join(_settingsDirectory, 'baram.cfg.yaml')
    _applicationLockFile = os.path.join(_settingsDirectory, 'baram.lock')

    @classmethod
    def init(cls):
        if not os.path.isdir(cls._settingsDirectory):
            os.mkdir(cls._settingsDirectory)

        if not os.path.isdir(cls._casesDirectory):
            os.mkdir(cls._casesDirectory)

    @classmethod
    def casesDirectory(cls):
        return cls._casesDirectory

    @classmethod
    def acquireLock(cls, timeout):
        try:
            lock = FileLock(cls._applicationLockFile)
            lock.acquire(timeout=timeout)
            return lock
        except Timeout:
            return None

    @classmethod
    def getRecentDirectory(cls):
        return cls._get(SettingKey.RECENT_DIRECTORY, cls._userDirectory)

    @classmethod
    def getRecentCases(cls):
        return cls._get(SettingKey.RECENT_CASES, [])

    @classmethod
    def updateRecents(cls, project, new):
        settings = cls._load()
        if new:
            settings[SettingKey.RECENT_DIRECTORY.value] = os.path.dirname(project.directory)

        recentCases\
            = settings[SettingKey.RECENT_CASES.value] if SettingKey.RECENT_CASES.value in settings else []
        if project.uuid in recentCases:
            recentCases.remove(project.uuid)
        recentCases.insert(0, project.uuid)
        settings[SettingKey.RECENT_CASES.value] = recentCases[:RECENT_CASES_NUMBER]
        cls._save(settings)

    @classmethod
    def _load(cls):
        if os.path.isfile(cls._settingsFile):
            with open(cls._settingsFile) as file:
                return yaml.load(file, Loader=yaml.FullLoader)
        else:
            return {SettingKey.FORMAT_VERSION.value: FORMAT_VERSION}

    @classmethod
    def _save(cls, settings):
        with open(cls._settingsFile, 'w') as file:
            yaml.dump(settings, file)

    @classmethod
    def _get(cls, key, defauilt=None):
        settings = cls._load()
        return settings[key.value] if key.value in settings else defauilt
