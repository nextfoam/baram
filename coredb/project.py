#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import uuid
from enum import IntEnum, auto, Enum

import yaml
from PySide6.QtCore import QObject, Signal
from pathlib import Path


FORMAT_VERSION = 1


class CaseStatus(IntEnum):
    CREATED = 0
    MESH_LOADED = auto()


class ProjectSettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    CASE_UUID = 'case_uuid'
    CASE_FULL_PATH = 'case_full_path'


class LocalSettings:
    def __init__(self, projectDirectory):
        self._settingsFile = os.path.join(projectDirectory, 'baram.cfg')
        self._settings = None

        self._load()

    def getId(self):
        return self._get(ProjectSettingKey.CASE_UUID)

    def save(self, project):
        settings = {
            ProjectSettingKey.FORMAT_VERSION.value: FORMAT_VERSION,
            ProjectSettingKey.CASE_UUID.value: project.uuid,
            ProjectSettingKey.CASE_FULL_PATH.value: project.directory
        }

        with open(self._settingsFile, 'w') as file:
            yaml.dump(settings, file)

    def _load(self):
        if os.path.isfile(self._settingsFile):
            with open(self._settingsFile) as file:
                self._settings = yaml.load(file, Loader=yaml.FullLoader)

    def _get(self, key):
        if self._settings:
            return self._settings[key.value]

        return None


class Project(QObject):
    statusChanged = Signal(CaseStatus)

    _directory = None
    _uuid = None
    _status = CaseStatus.CREATED

    def __init__(self, directory):
        super().__init__()
        self._directory = str(Path(directory).resolve())
        self._localSettings = LocalSettings(self._directory)
        self._uuid = self._localSettings.getId()

    @property
    def uuid(self):
        return self._uuid

    @property
    def directory(self):
        return self._directory

    @property
    def name(self):
        return os.path.basename(self._directory)

    def renewId(self):
        self._uuid = str(uuid.uuid4())

    def status(self):
        return self._status

    def setStatus(self, status):
        self._status = status
        self.statusChanged.emit(status)

    def saveSettings(self):
        self._localSettings.save(self)
