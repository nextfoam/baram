#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os

import yaml
from filelock import FileLock, Timeout

from coredb.settings import Settings
from .project import ProjectSettingKey


SETTINGS_FILE_NAME = 'case.cfg.yaml'
FORMAT_VERSION = 1


class ProjectSettings:
    _settingsDirectory = None
    _settingsFile = None

    def __init__(self, project):
        self._projectLock = None

        fullPath = None

        if project.uuid:
            self._setupSettingPaths(project)
            fullPath = self.get(ProjectSettingKey.CASE_FULL_PATH)

        if not fullPath or (fullPath != project.directory and os.path.isdir(fullPath)):
            # If setting is None, fullPath is also None and the project is just created or copied from somewhere.
            # If fullPath exists but is different from project's directory, the project was copied from fullPath.
            # In both cases above, the project is treated as new.
            # So, add new project settings and return new uuid.
            self._addSettings(project)
        elif not os.path.isdir(fullPath):
            # fullPath means origin path of the project.
            # And if fullPath is not None and does not exist in file system, then the project has been moved(renamed).
            # So, update project settings with correct fullPath
            self._save(project)

    def get(self, key):
        settings = self._load()
        if settings:
            return settings[key.value] if key.value in settings else None

        return None

    def acquireLock(self, timeout):
        try:
            lockFile = os.path.join(self._settingsDirectory, 'case.lock')
            self._projectLock = FileLock(lockFile)
            self._projectLock.acquire(timeout=timeout)

            return True
        except Timeout:
            return False

    def releaseLock(self):
        self._projectLock.release()

    @classmethod
    def loadSettings(cls, projectId):
        settingsFile = os.path.join(Settings.casesDirectory(), projectId, SETTINGS_FILE_NAME)
        if os.path.isfile(settingsFile):
            with open(settingsFile) as file:
                return yaml.load(file, Loader=yaml.FullLoader)
        else:
            return None

    def _addSettings(self, project):
        project.renewId()
        self._setupSettingPaths(project)
        os.mkdir(self._settingsDirectory)

        project.saveSettings()
        self._save(project)

    def _load(self):
        if os.path.isfile(self._settingsFile):
            with open(self._settingsFile) as file:
                return yaml.load(file, Loader=yaml.FullLoader)
        else:
            return None

    def _save(self, project):
        settings = {
            ProjectSettingKey.FORMAT_VERSION.value: FORMAT_VERSION,
            ProjectSettingKey.CASE_UUID.value: project.uuid,
            ProjectSettingKey.CASE_FULL_PATH.value: project.directory
        }

        with open(self._settingsFile, 'w') as file:
            yaml.dump(settings, file)

    def _setupSettingPaths(self, project):
        self._settingsDirectory = os.path.join(Settings.casesDirectory(), project.uuid)
        self._settingsFile = os.path.join(self._settingsDirectory, SETTINGS_FILE_NAME)
