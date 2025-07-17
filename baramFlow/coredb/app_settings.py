#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import platform
import shutil
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml
from filelock import FileLock
from PySide6.QtCore import QLocale, QRect

from libbaram.mpi import ParallelEnvironment, ParallelType
from resources import resource

from baramFlow.coredb.materials_base import MaterialsBase

FORMAT_VERSION = 1
RECENT_PROJECTS_NUMBER = 100

MATERIALS_FILE_NAME = 'materials.csv'


class SettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    UI_SCALING = 'ui_scaling'
    LOCALE = 'default_language'
    RECENT_DIRECTORY = 'recent_directory'
    RECENT_CASES = 'recent_cases'
    RECENT_MESH_DIRECTORY = 'recent_mesh_directory'
    LAST_START_WINDOW_GEOMETRY = 'last_start_window_position'
    LAST_MAIN_WINDOW_GEOMETRY = 'last_main_window_position'
    PARAVIEW_INSTALLED_PATH = 'paraview_installed_path'
    PARALLEL_NP = 'parallel_np'
    PARALLEL_TYPE = 'parallel_type'
    PARALLEL_HOSTFILE = 'parallel_hostfile'


class AppSettings:
    _settingsPath = None
    _casesPath = None
    _settingsFile = None
    _applicationLockFile = None
    _settings = None

    @classmethod
    def setup(cls, name):
        cls._settingsPath = Path.home() / f'.{name}'
        cls._casesPath = cls._settingsPath / 'cases'
        cls._settingsFile = cls._settingsPath / 'baram.cfg.yaml'
        cls._applicationLockFile = cls._settingsPath / 'baram.lock'
        cls._materialsDBFile = cls._settingsPath / MATERIALS_FILE_NAME

        # ToDo: For compatibility. Remove this code block after 20241201
        # Migration from previous name of "BaramFlow"
        # Begin
        if name == 'BaramFlow':
            oldPath = Path.home().joinpath('.baram')
            if not cls._settingsPath.exists() and oldPath.is_dir():
                oldPath.replace(cls._settingsPath)
        # End

        cls._settingsPath.mkdir(exist_ok=True)
        cls._casesPath.mkdir(exist_ok=True)

        if not cls._materialsDBFile.exists():
            shutil.copy(resource.file(MATERIALS_FILE_NAME), cls._materialsDBFile)
        MaterialsBase.load(cls._materialsDBFile)

    @classmethod
    def casesPath(cls):
        return cls._casesPath

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
    def getLastStartWindowGeometry(cls) -> QRect:
        x, y, width, height = cls._get(SettingKey.LAST_START_WINDOW_GEOMETRY, [200, 100, 400, 300])
        return QRect(x, y, width, height)

    @classmethod
    def updateLastStartWindowGeometry(cls, geometry: QRect):
        settings = cls._load()
        settings[SettingKey.LAST_START_WINDOW_GEOMETRY.value] = [geometry.x(), geometry.y(), geometry.width(), geometry.height()]
        cls._save(settings)

    @classmethod
    def getLastMainWindowGeometry(cls) -> QRect:
        x, y, width, height = cls._get(SettingKey.LAST_MAIN_WINDOW_GEOMETRY, [200, 100, 1280, 770])
        return QRect(x, y, width, height)

    @classmethod
    def updateLastMainWindowGeometry(cls, geometry: QRect):
        settings = cls._load()
        settings[SettingKey.LAST_MAIN_WINDOW_GEOMETRY.value] = [geometry.x(), geometry.y(), geometry.width(), geometry.height()]
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
    def updateParaviewInstalledPath(cls, path: Path):
        settings = cls._load()
        settings[SettingKey.PARAVIEW_INSTALLED_PATH.value] = str(path)
        cls._save(settings)

    @classmethod
    def findParaviewInstalledPath(cls) -> Optional[Path]:
        def validate(pathString: str, update=True):
            if pathString:
                p = Path(pathString)
                if p.is_file():
                    if update:
                        cls.updateParaviewInstalledPath(p)

                    return p

            return None

        if path := validate(cls._get(SettingKey.PARAVIEW_INSTALLED_PATH, ''), False):
            return path

        if path := validate(shutil.which('paraview')):
            return path

        if platform.system() == 'Windows':
            # Search the unique paraview executable file.
            paraviewHomes = list(Path(os.environ.get('PROGRAMFILES')).glob('paraview*'))
            if len(paraviewHomes) == 1:
                if path := validate(str(paraviewHomes[0] / 'bin/paraview.exe')):
                    return path

        return None
    
    @classmethod
    def getParallenEnvironment(cls):
        settings = cls._load()
        type_ = settings.get(SettingKey.PARALLEL_TYPE.value)
        
        return ParallelEnvironment(
            settings.get(SettingKey.PARALLEL_NP.value, 1),
            ParallelType.LOCAL_MACHINE if type_ is None else ParallelType[type_],
            settings.get(SettingKey.PARALLEL_HOSTFILE.value))
        
    @classmethod
    def setParallelEnvironment(cls, environment):
        settings = cls._load()
        settings[SettingKey.PARALLEL_NP.value] = environment.np()
        settings[SettingKey.PARALLEL_TYPE.value] = environment.type().name
        settings[SettingKey.PARALLEL_HOSTFILE.value] = environment.hosts()
        cls._save(settings)

    @classmethod
    def _load(cls):
        if cls._settingsFile.is_file():
            with open(cls._settingsFile) as file:
                return yaml.load(file, Loader=yaml.FullLoader)
        else:
            return {}

    @classmethod
    def _save(cls, settings):
        settings[SettingKey.FORMAT_VERSION.value] = FORMAT_VERSION

        with open(cls._settingsFile, 'w') as file:
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

    @classmethod
    def updateMaterialsDB(cls, materials):
        df = pd.DataFrame.from_dict(materials, orient='index')
        df.to_csv(cls._materialsDBFile, index_label='name')

        MaterialsBase.update(materials)
