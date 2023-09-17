#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
from pathlib import Path

from PySide6.QtCore import QLocale, QRect

import yaml
from filelock import FileLock, Timeout


FORMAT_VERSION = 1
RECENT_PROJECTS_NUMBER = 100


class SettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    SCALE = 'display_scale'
    LOCALE = 'default_language'
    RECENT_DIRECTORY = 'recent_directory'
    RECENT_CASES = 'recent_cases'
    RECENT_MESH_DIRECTORY = 'recent_mesh_directory'
    LAST_START_WINDOW_GEOMETRY = 'LAST_START_WINDOW_GEOMETRY'
    LAST_MAIN_WINDOW_GEOMETRY = 'LAST_MAIN_WINDOW_GEOMETRY'
    PARAVIEW_INSTALLED_PATH = 'paraview_installed_path'


class AppSettings:
    _settingsPath = None
    _settingsFile = None
    _lockFile = None

    def __init__(self, name):
        self._settingsPath = Path.home() / f'.{name}'
        self._settingsFile = self._settingsPath / 'baram.cfg.yaml'
        self._lockFile = self._settingsPath / 'baram.lock'

        self._lock = None

        self._settingsPath.mkdir(exist_ok=True)

    def acquireLock(self, timeout):
        try:
            self._lock = FileLock(self._lockFile)
            self._lock.acquire(timeout=timeout)

            return True
        except Timeout:
            return False

    def releaseLock(self):
        self._lock.release()

    def getRecentLocation(self):
        return self._get(SettingKey.RECENT_DIRECTORY, str(Path.home()))

    def getRecentProjects(self):
        return self._get(SettingKey.RECENT_CASES, [])

    def updateRecents(self, path, new=False):
        settings = self._load()
        if new:
            settings[SettingKey.RECENT_DIRECTORY.value] = str(path.parent)

        p = str(path)
        recentCases\
            = settings[SettingKey.RECENT_CASES.value] if SettingKey.RECENT_CASES.value in settings else []
        if p in recentCases:
            recentCases.remove(p)
        recentCases.insert(0, p)
        settings[SettingKey.RECENT_CASES.value] = recentCases[:RECENT_PROJECTS_NUMBER]
        self._save(settings)

    def getLastStartWindowGeometry(self) -> QRect:
        x, y, width, height = self._get(SettingKey.LAST_START_WINDOW_GEOMETRY, [200, 100, 400, 300])
        return QRect(x, y, width, height)

    def updateLastStartWindowGeometry(self, geometry: QRect):
        self._set(SettingKey.LAST_START_WINDOW_GEOMETRY, [geometry.x(), geometry.y(), geometry.width(), geometry.height()])

    def getLastMainWindowGeometry(self) -> QRect:
        x, y, width, height = self._get(SettingKey.LAST_MAIN_WINDOW_GEOMETRY, [200, 100, 1280, 770])
        return QRect(x, y, width, height)

    def updateLastMainWindowGeometry(self, geometry: QRect):
        self._set(SettingKey.LAST_MAIN_WINDOW_GEOMETRY, [geometry.x(), geometry.y(), geometry.width(), geometry.height()]
                  )

    def getScale(self):
        return self._get(SettingKey.SCALE, '1.0')

    def setScale(self, scale):
        return self._set(SettingKey.SCALE, scale)

    # Territory is not considered for now
    def getLocale(self) -> QLocale:
        return QLocale(QLocale.languageToCode(QLocale(self.getLanguage()).language()))

    def getLanguage(self):
        return self._get(SettingKey.LOCALE, 'en')

    def setLanguage(self, language):
        return self._set(SettingKey.LOCALE, language)

    def getParaviewInstalledPath(self):
        return self._get(SettingKey.PARAVIEW_INSTALLED_PATH, '')

    def updateParaviewInstalledPath(self, path):
        self._set(SettingKey.PARAVIEW_INSTALLED_PATH, path)

    def _load(self):
        if self._settingsFile.is_file():
            with open(self._settingsFile) as file:
                return yaml.load(file, Loader=yaml.FullLoader)
        else:
            return {}

    def _save(self, settings):
        settings[SettingKey.FORMAT_VERSION.value] = FORMAT_VERSION

        with open(self._settingsFile, 'w') as file:
            yaml.dump(settings, file)

    def _get(self, key, default=None):
        settings = self._load()
        return settings[key.value] if key.value in settings else default

    def _set(self, key, value):
        settings = self._load()
        if key.value in settings and settings[key.value] == value:
            return False

        settings[key.value] = value
        self._save(settings)

        return True

    def removeProject(self, num):
        project = self.getRecentProjects()

        settings = self._load()
        recentCases \
            = settings[SettingKey.RECENT_CASES.value] if SettingKey.RECENT_CASES.value in settings else []
        if project[num] in recentCases:
            recentCases.remove(project[num])
        self._save(settings)
