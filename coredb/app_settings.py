#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
from enum import Enum

import yaml
from filelock import FileLock


FORMAT_VERSION = 1
RECENT_CASES_NUMBER = 5

userDirectory = os.path.join(os.path.expanduser('~'), 'baram')
settingsDirectory = os.path.join(os.path.expanduser('~'), '.baram')
casesDirectory = os.path.join(settingsDirectory, 'cases')
settingsFile = os.path.join(settingsDirectory, 'baram.cfg.yaml')

if not os.path.isdir(settingsDirectory):
    os.mkdir(settingsDirectory)

if not os.path.isdir(casesDirectory):
    os.mkdir(casesDirectory)


class SettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    DISPLAY_SCALE = 'display_scale'
    RECENT_DIRECTORY = 'recent_directory'
    RECENT_CASES = 'recent_cases'


class AppSettings:
    _applicationLockFile = os.path.join(settingsDirectory, 'baram.lock')

    @classmethod
    def casesDirectory(cls):
        return casesDirectory

    @classmethod
    def acquireLock(cls, timeout):
        lock = FileLock(cls._applicationLockFile)
        lock.acquire(timeout=timeout)
        return lock

    @classmethod
    def getRecentDirectory(cls):
        return cls._get(SettingKey.RECENT_DIRECTORY, userDirectory)

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
        if os.path.isfile(settingsFile):
            with open(settingsFile) as file:
                return yaml.load(file, Loader=yaml.FullLoader)
        else:
            return {SettingKey.FORMAT_VERSION.value: FORMAT_VERSION}

    @classmethod
    def _save(cls, settings):
        with open(settingsFile, 'w') as file:
            yaml.dump(settings, file)

    @classmethod
    def _get(cls, key, default=None):
        settings = cls._load()
        return settings[key.value] if key.value in settings else default
