#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
from pathlib import Path

import yaml
from filelock import FileLock, Timeout
from PySide6.QtCore import QLocale, QRect

from libbaram.mpi import ParallelEnvironment, ParallelType


FORMAT_VERSION = 1
RECENT_PROJECTS_NUMBER = 100


class SettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    SCALE = 'display_scale'
    LOCALE = 'default_language'
    RECENT_DIRECTORY = 'recent_directory'
    RECENT_CASES = 'recent_cases'
    RECENT_IMPORT_DIRECTORY = 'recent_import_directory'
    LAST_START_WINDOW_GEOMETRY = 'LAST_START_WINDOW_GEOMETRY'
    LAST_MAIN_WINDOW_GEOMETRY = 'LAST_MAIN_WINDOW_GEOMETRY'
    PARAVIEW_INSTALLED_PATH = 'paraview_installed_path'
    PARALLEL_NP = 'parallel_np'
    PARALLEL_TYPE = 'parallel_type'
    PARALLEL_HOSTFILE = 'parallel_hostfile'


class AppSettings:
    def __init__(self):
        self._settings = None

        self._settingsFile = None
        # self._lockFile = None
        self._lock = None
        
        
    def load(self, name):
        path = Path.home() / f'.{name}'
        self._settingsFile = path / 'baram.cfg.yaml'
        # self._lockFile = path / 'baram.lock'

        # ToDo: For compatibility. Remove this code block after 20240101
        # Migration from previous name of "BaramMesh"
        # Begin
        if name == 'BaramMesh':
            oldPath = Path.home().joinpath('.baram-snappy')
            if not path.exists() and oldPath.is_dir():
                oldPath.replace(path)
        # End

        if self._settingsFile.is_file():
            with open(self._settingsFile) as file:
                self._settings = yaml.load(file, Loader=yaml.FullLoader)
        else:
            self._settingsPath.mkdir(exist_ok=True)
            self._settings = {SettingKey.FORMAT_VERSION.value: FORMAT_VERSION}

    def getRecentLocation(self):
        return self._get(SettingKey.RECENT_DIRECTORY, str(Path.home()))

    def getRecentProjects(self):
        return self._get(SettingKey.RECENT_CASES, [])

    def updateRecents(self, path, new=False):
        if new:
            self._settings[SettingKey.RECENT_DIRECTORY.value] = str(path.parent)

        p = str(path)
        recentCases\
            = self._settings[SettingKey.RECENT_CASES.value] if SettingKey.RECENT_CASES.value in self._settings else []
        if p in recentCases:
            recentCases.remove(p)
        recentCases.insert(0, p)
        self._settings[SettingKey.RECENT_CASES.value] = recentCases[:RECENT_PROJECTS_NUMBER]
        self._save()

    def getRecentImportDirectory(self):
        return self._get(SettingKey.RECENT_IMPORT_DIRECTORY, str(Path.home()))

    def updateRecentImportDirectory(self, path):
        self._set(SettingKey.RECENT_IMPORT_DIRECTORY, str(path))

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

    def getParallenEnvironment(self):
        np = self._get(SettingKey.PARALLEL_NP)
        type_ = self._get(SettingKey.PARALLEL_TYPE)
        
        return ParallelEnvironment(
            1 if np is None else int(np),
            ParallelType.LOCAL_MACHINE if type_ is None else ParallelType[type_],
            self._get(SettingKey.PARALLEL_HOSTFILE))

    def updateParallelEnvironment(self, environment):
        self._set(SettingKey.PARALLEL_NP, environment.np())
        self._set(SettingKey.PARALLEL_TYPE, environment.type().name)
        self._set(SettingKey.PARALLEL_HOSTFILE, environment.hosts())
        self._save()

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

    def _save(self):
        with open(self._settingsFile, 'w') as file:
            yaml.dump(self._settings, file)

    def _get(self, key, default=None):
        return self._settings[key.value] if key.value in self._settings else default

    def _set(self, key, value):
        if key.value in self._settings and self._settings[key.value] == value:
            return False

        self._settings[key.value] = value
        self._save()

        return True

    def removeProject(self, num):
        project = self.getRecentProjects()

        recentCases = (self._settings[SettingKey.RECENT_CASES.value] if SettingKey.RECENT_CASES.value in self._settings
                       else [])
        if project[num] in recentCases:
            recentCases.remove(project[num])

        self._save()


appSettings = AppSettings()