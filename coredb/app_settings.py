#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import screeninfo
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QLocale, QRect

import yaml
from filelock import FileLock


FORMAT_VERSION = 1
RECENT_PROJECTS_NUMBER = 100

settingsPath = Path.home() / '.baram'
casesPath = settingsPath / 'cases'
settingsFile = settingsPath / 'baram.cfg.yaml'

settingsPath.mkdir(exist_ok=True)
casesPath.mkdir(exist_ok=True)


class SettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    UI_SCALING = 'ui_scaling'
    LOCALE = 'default_language'
    RECENT_DIRECTORY = 'recent_directory'
    RECENT_CASES = 'recent_cases'
    RECENT_MESH_DIRECTORY = 'recent_mesh_directory'
    LAST_START_WINDOW_POSITION = 'last_start_window_position'
    LAST_MAIN_WINDOW_POSITION = 'last_main_window_position'
    PARAVIEW_INSTALLED_PATH = 'paraview_installed_path'


class AppSettings:
    _applicationLockFile = settingsPath / 'baram.lock'

    @classmethod
    def casesPath(cls):
        return casesPath

    @classmethod
    def acquireLock(cls, timeout):
        lock = FileLock(cls._applicationLockFile)
        lock.acquire(timeout=timeout)
        return lock

    @classmethod
    def getRecentLocation(cls):
        return cls._get(SettingKey.RECENT_DIRECTORY, str(Path.home()))

    @classmethod
    def getRecentProjects(cls, count):
        projects = cls._get(SettingKey.RECENT_CASES, [])
        return projects[:count]

    @classmethod
    def updateRecents(cls, project, new):
        settings = cls._load()
        if new:
            settings[SettingKey.RECENT_DIRECTORY.value] = str(project.path.parent)

        recentCases\
            = settings[SettingKey.RECENT_CASES.value] if SettingKey.RECENT_CASES.value in settings else []
        if project.uuid in recentCases:
            recentCases.remove(project.uuid)
        recentCases.insert(0, project.uuid)
        settings[SettingKey.RECENT_CASES.value] = recentCases[:RECENT_PROJECTS_NUMBER]
        cls._save(settings)

    @classmethod
    def getRecentMeshDirectory(cls):
        return cls._get(SettingKey.RECENT_MESH_DIRECTORY, os.path.expanduser('~'))

    @classmethod
    def updateRecentMeshDirectory(cls, path):
        settings = cls._load()
        settings[SettingKey.RECENT_MESH_DIRECTORY.value] = path
        cls._save(settings)

    @classmethod
    def getPrimaryMonitor(cls):
        monitorsInfo = screeninfo.get_monitors()
        for i, d in enumerate(monitorsInfo):
            if d.is_primary:
                return i
        return 0

    @classmethod
    def getMonitorSize(cls, monitorNum=-1):
        monitorsInfo = screeninfo.get_monitors()
        if monitorNum < 0 or monitorNum >= len(monitorsInfo):
            monitorNum = cls.getPrimaryMonitor()

        x = monitorsInfo[monitorNum].x
        y = monitorsInfo[monitorNum].y
        width = monitorsInfo[monitorNum].width
        height = monitorsInfo[monitorNum].height
        return [x, y, width, height]

    @classmethod
    def _getWindowProperPosition(cls, position):
        x, y, width, height = position
        minX, minY, maxX, maxY = 0, 0, 0, 0
        scaling = float(AppSettings.getUiScaling())

        monitorsInfo = screeninfo.get_monitors()
        for d in monitorsInfo:
            minX = (min(minX, d.x) / scaling)
            minY = (min(minY, d.y) / scaling)
            maxX = (max(maxX, d.x + d.width) / scaling)
            maxY = (max(maxY, d.y + d.height) / scaling)

        if minX <= (x / scaling) <= (maxX - (width / scaling)) and minY <= (y / scaling) <= (maxY - (height / scaling)):
            return [x, y, width, height]
        return cls.getWindowCenterPosition(width, height, scaling)

    @classmethod
    def getWindowCenterPosition(cls, width=400, height=300, scaling=1.0):
        monitorSize = cls.getMonitorSize()
        x = ((monitorSize[2] / 2) - (width / 2) + monitorSize[0]) / scaling
        y = ((monitorSize[3] / 2) - (height / 2)) / scaling
        return [x, y, width, height]

    @classmethod
    def getLastStartWindowPosition(cls):
        position = cls._get(SettingKey.LAST_START_WINDOW_POSITION, cls.getWindowCenterPosition(400, 300))
        return cls._getWindowProperPosition(position)

    @classmethod
    def updateLastStartWindowPosition(cls, rect):
        settings = cls._load()
        settings[SettingKey.LAST_START_WINDOW_POSITION.value] = [rect[0], rect[1], rect[2], rect[3]]
        cls._save(settings)

    @classmethod
    def getLastMainWindowPosition(cls) -> QRect:
        position = cls._get(SettingKey.LAST_MAIN_WINDOW_POSITION, cls.getWindowCenterPosition(1280, 770))
        return QRect(*cls._getWindowProperPosition(position))

    @classmethod
    def updateLastMainWindowPosition(cls, rect: QRect):
        settings = cls._load()
        settings[SettingKey.LAST_MAIN_WINDOW_POSITION.value] = rect.getRect()
        cls._save(settings)

    @classmethod
    def getUiScaling(cls):
        return cls._get(SettingKey.UI_SCALING, '1.0')

    @classmethod
    def updateUiScaling(cls, scaling):
        settings = cls._load()
        settings[SettingKey.UI_SCALING.value] = scaling
        cls._save(settings)

    # Territory is not considered for now
    @classmethod
    def getLocale(cls) -> QLocale:
        return QLocale(QLocale.languageToCode(QLocale(cls.getLanguage()).language()))

    @classmethod
    def getLanguage(cls):
        return cls._get(SettingKey.LOCALE, 'en')

    @classmethod
    def setLanguage(cls, language):
        settings = cls._load()
        settings[SettingKey.LOCALE.value] = language
        cls._save(settings)

    @classmethod
    def getParaviewInstalledPath(cls):
        return cls._get(SettingKey.PARAVIEW_INSTALLED_PATH, '')

    @classmethod
    def updateParaviewInstalledPath(cls, path):
        settings = cls._load()
        settings[SettingKey.PARAVIEW_INSTALLED_PATH.value] = path
        cls._save(settings)

    @classmethod
    def _load(cls):
        if settingsFile.is_file():
            with open(settingsFile) as file:
                return yaml.load(file, Loader=yaml.FullLoader)
        else:
            return {}

    @classmethod
    def _save(cls, settings):
        settings[SettingKey.FORMAT_VERSION.value] = FORMAT_VERSION

        with open(settingsFile, 'w') as file:
            yaml.dump(settings, file)

    @classmethod
    def _get(cls, key, default=None):
        settings = cls._load()
        return settings[key.value] if key.value in settings else default

    @classmethod
    def removeProject(cls, num):
        project = AppSettings.getRecentProjects(RECENT_PROJECTS_NUMBER)

        settings = cls._load()
        recentCases \
            = settings[SettingKey.RECENT_CASES.value] if SettingKey.RECENT_CASES.value in settings else []
        if project[num] in recentCases:
            recentCases.remove(project[num])
        cls._save(settings)
